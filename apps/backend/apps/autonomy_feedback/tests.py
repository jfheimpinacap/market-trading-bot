from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.memory_retrieval.models import MemoryDocument


class AutonomyFeedbackTests(TestCase):
    def _campaign(self, title='Feedback Campaign', status='COMPLETED'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='feedback test',
            metadata={'domains': ['autonomy']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def _closeout(self, campaign):
        return CampaignCloseoutReport.objects.create(
            campaign=campaign,
            disposition_type='CLOSED',
            closeout_status='COMPLETED',
            executive_summary='done',
            lifecycle_summary={},
            major_blockers=[],
            incident_summary={},
            intervention_summary={},
            recovery_summary={},
            final_outcome_summary='stable',
            closed_out_by='tests',
            closed_out_at=timezone.now(),
            metadata={},
        )

    def _followup(self, campaign, closeout, followup_type='MEMORY_INDEX', **overrides):
        defaults = {
            'campaign': campaign,
            'closeout_report': closeout,
            'followup_type': followup_type,
            'followup_status': 'EMITTED',
            'rationale': 'track resolution',
            'reason_codes': ['tests'],
            'blockers': [],
            'metadata': {},
        }
        defaults.update(overrides)
        return CampaignFollowup.objects.create(**defaults)

    def test_candidates_only_include_emitted_followups(self):
        campaign = self._campaign()
        closeout = self._closeout(campaign)
        emitted = self._followup(campaign, closeout, followup_status='EMITTED')
        self._followup(campaign, closeout, followup_status='DUPLICATE_SKIPPED')

        response = self.client.get(reverse('autonomy_feedback:candidates'))
        self.assertEqual(response.status_code, 200)
        ids = {row['followup'] for row in response.json()}
        self.assertIn(emitted.id, ids)
        self.assertEqual(len(ids), 1)

    def test_run_review_does_not_override_completed_resolution(self):
        campaign = self._campaign(title='No duplicate close')
        closeout = self._closeout(campaign)
        doc = MemoryDocument.objects.create(
            document_type='lifecycle_decision',
            source_app='tests',
            source_object_id=f'campaign:{campaign.id}',
            title='memory linked',
            text_content='resolved',
        )
        followup = self._followup(campaign, closeout, linked_memory_document=doc)
        FollowupResolution.objects.create(
            campaign=campaign,
            followup=followup,
            resolution_status='COMPLETED',
            downstream_status='COMPLETED',
            resolution_type='MEMORY_RESOLVED',
            rationale='already completed',
            reason_codes=['seeded'],
            blockers=[],
        )

        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')
        resolution = FollowupResolution.objects.get(followup=followup)
        self.assertEqual(resolution.resolution_status, 'COMPLETED')
        self.assertEqual(FollowupResolution.objects.filter(followup=followup).count(), 1)

    def test_memory_followup_resolves_when_document_linked(self):
        campaign = self._campaign(title='Memory resolved')
        closeout = self._closeout(campaign)
        doc = MemoryDocument.objects.create(
            document_type='lifecycle_decision',
            source_app='tests',
            source_object_id=f'campaign:{campaign.id}:memory',
            title='linked',
            text_content='ok',
        )
        followup = self._followup(campaign, closeout, linked_memory_document=doc)

        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')
        resolution = FollowupResolution.objects.get(followup=followup)
        self.assertEqual(resolution.resolution_status, 'COMPLETED')

    def test_postmortem_followup_pending_tracks_open_request(self):
        campaign = self._campaign(title='Postmortem pending')
        closeout = self._closeout(campaign)
        request = ApprovalRequest.objects.create(
            source_type='other',
            source_object_id=f'postmortem:{campaign.id}',
            title='Need postmortem',
            summary='pending',
            priority='HIGH',
            status='PENDING',
            requested_at=timezone.now(),
        )
        followup = self._followup(campaign, closeout, followup_type='POSTMORTEM_REQUEST', linked_postmortem_request=request)

        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')
        resolution = FollowupResolution.objects.get(followup=followup)
        self.assertEqual(resolution.resolution_status, 'PENDING')

    def test_roadmap_feedback_pending_without_review_signal(self):
        campaign = self._campaign(title='Roadmap pending')
        closeout = self._closeout(campaign)
        followup = self._followup(campaign, closeout, followup_type='ROADMAP_FEEDBACK', linked_feedback_artifact='roadmap-feedback:1')

        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')
        resolution = FollowupResolution.objects.get(followup=followup)
        self.assertEqual(resolution.resolution_status, 'IN_PROGRESS')

    def test_complete_resolution_is_auditable(self):
        campaign = self._campaign(title='Manual complete')
        closeout = self._closeout(campaign)
        doc = MemoryDocument.objects.create(
            document_type='lifecycle_decision',
            source_app='tests',
            source_object_id=f'campaign:{campaign.id}:complete',
            title='linked',
            text_content='ok',
        )
        followup = self._followup(campaign, closeout, linked_memory_document=doc)
        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')

        response = self.client.post(reverse('autonomy_feedback:complete', kwargs={'followup_id': followup.id}), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        resolution = FollowupResolution.objects.get(followup=followup)
        self.assertEqual(resolution.resolution_status, 'CLOSED')
        self.assertTrue(resolution.resolved_by)

    def test_summary_endpoint(self):
        campaign = self._campaign(title='Summary')
        closeout = self._closeout(campaign)
        self._followup(campaign, closeout, followup_type='ROADMAP_FEEDBACK', linked_feedback_artifact='artifact:summary')
        self.client.post(reverse('autonomy_feedback:run_review'), data={}, content_type='application/json')

        response = self.client.get(reverse('autonomy_feedback:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())
