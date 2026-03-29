from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.models import AutonomyCampaignCheckpoint
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutRecommendation
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.incident_commander.models import IncidentRecord


class AutonomyCloseoutTests(TestCase):
    def _create_campaign(self, *, status: str = 'COMPLETED', title: str = 'Closeout Campaign', metadata: dict | None = None):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='closeout',
            metadata=metadata or {'domains': ['rollout_controls']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def _create_disposition(self, campaign, *, disposition_type='CLOSED', disposition_status='APPLIED', blockers=None):
        return CampaignDisposition.objects.create(
            campaign=campaign,
            disposition_type=disposition_type,
            disposition_status=disposition_status,
            rationale='final disposition',
            reason_codes=['tests'],
            blockers=blockers or [],
            requires_approval=False,
            campaign_state_before=campaign.status,
            campaign_state_after=campaign.status,
        )

    def test_candidates_select_ready_for_closeout(self):
        campaign = self._create_campaign()
        self._create_disposition(campaign, disposition_type='COMPLETED_RECORDED', disposition_status='APPLIED')

        response = self.client.get(reverse('autonomy_closeout:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = next(item for item in response.json() if item['campaign'] == campaign.id)
        self.assertTrue(payload['ready_for_closeout'])

    def test_complete_closeout_blocked_when_critical_gates_open(self):
        campaign = self._create_campaign()
        self._create_disposition(campaign, disposition_type='CLOSED', blockers=['manual_block'])
        self.client.post(reverse('autonomy_closeout:run_review'), data={}, content_type='application/json')

        response = self.client.post(reverse('autonomy_closeout:complete', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_send_to_postmortem_for_abort_with_incidents(self):
        campaign = self._create_campaign(status='ABORTED')
        self._create_disposition(campaign, disposition_type='ABORTED')
        IncidentRecord.objects.create(
            incident_type='runtime_conflict',
            severity='critical',
            status='OPEN',
            title='Critical incident',
            summary='incident',
            source_app='autonomy_campaign',
            related_object_type='autonomy_campaign',
            related_object_id=str(campaign.id),
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )

        self.client.post(reverse('autonomy_closeout:run_review'), data={}, content_type='application/json')
        self.assertTrue(
            CloseoutRecommendation.objects.filter(target_campaign=campaign, recommendation_type='SEND_TO_POSTMORTEM').exists()
        )

    def test_index_memory_or_roadmap_feedback_recommendations(self):
        memory_campaign = self._create_campaign(title='Memory campaign')
        self._create_disposition(memory_campaign, disposition_type='COMPLETED_RECORDED')

        roadmap_campaign = self._create_campaign(title='Roadmap feedback campaign')
        self._create_disposition(roadmap_campaign, disposition_type='CLOSED', blockers=['open_checkpoints'])
        step = roadmap_campaign.steps.order_by('id').first()
        AutonomyCampaignCheckpoint.objects.create(
            campaign=roadmap_campaign,
            step=step,
            checkpoint_type='DEPENDENCY_CONFLICT',
            status='OPEN',
            summary='dependency friction',
        )

        self.client.post(reverse('autonomy_closeout:run_review'), data={}, content_type='application/json')
        self.assertTrue(
            CloseoutRecommendation.objects.filter(target_campaign=memory_campaign, recommendation_type='INDEX_IN_MEMORY').exists()
        )
        self.assertTrue(
            CloseoutRecommendation.objects.filter(target_campaign=roadmap_campaign, recommendation_type='PREPARE_ROADMAP_FEEDBACK').exists()
        )

    def test_complete_closeout_audited_when_clean(self):
        campaign = self._create_campaign()
        self._create_disposition(campaign, disposition_type='CLOSED')

        self.client.post(reverse('autonomy_closeout:run_review'), data={}, content_type='application/json')
        response = self.client.post(
            reverse('autonomy_closeout:complete', kwargs={'campaign_id': campaign.id}),
            data={'actor': 'test-operator'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        report = CampaignCloseoutReport.objects.get(campaign=campaign)
        self.assertEqual(report.closeout_status, 'COMPLETED')
        self.assertEqual(report.closed_out_by, 'test-operator')

    def test_summary_endpoint(self):
        campaign = self._create_campaign()
        self._create_disposition(campaign, disposition_type='COMPLETED_RECORDED')
        self.client.post(reverse('autonomy_closeout:run_review'), data={}, content_type='application/json')

        response = self.client.get(reverse('autonomy_closeout:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())

    def test_candidates_include_unresolved_approval_count(self):
        campaign = self._create_campaign()
        self._create_disposition(campaign, disposition_type='CLOSED')
        ApprovalRequest.objects.create(
            source_type='other',
            source_object_id=f'autonomy_campaign:{campaign.id}:pending',
            title='Pending approval',
            summary='approval',
            priority='HIGH',
            status='PENDING',
            requested_at=timezone.now(),
            metadata={'autonomy_campaign_id': campaign.id},
        )
        response = self.client.get(reverse('autonomy_closeout:candidates'))
        payload = next(item for item in response.json() if item['campaign'] == campaign.id)
        self.assertEqual(payload['unresolved_approvals_count'], 1)
