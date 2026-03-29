from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.memory_retrieval.models import MemoryDocument


class AutonomyFollowupTests(TestCase):
    def _campaign(self, title='Followup Campaign', status='COMPLETED'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='followup test',
            metadata={'domains': ['autonomy']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def _closeout_report(self, campaign, **overrides):
        defaults = {
            'disposition_type': 'CLOSED',
            'closeout_status': 'COMPLETED',
            'executive_summary': 'done',
            'lifecycle_summary': {},
            'major_blockers': [],
            'incident_summary': {},
            'intervention_summary': {},
            'recovery_summary': {},
            'final_outcome_summary': 'stable outcome',
            'requires_postmortem': False,
            'requires_memory_index': False,
            'requires_roadmap_feedback': False,
            'closed_out_by': 'test',
            'closed_out_at': timezone.now(),
            'metadata': {},
        }
        defaults.update(overrides)
        return CampaignCloseoutReport.objects.create(campaign=campaign, **defaults)

    def test_candidates_select_ready_for_followup(self):
        campaign = self._campaign()
        self._closeout_report(campaign, requires_memory_index=True)

        response = self.client.get(reverse('autonomy_followup:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = next(item for item in response.json() if item['campaign'] == campaign.id)
        self.assertIn(payload['followup_readiness'], ['READY', 'PARTIAL'])

    def test_emit_skip_duplicate_when_artifact_exists(self):
        campaign = self._campaign()
        document = MemoryDocument.objects.create(
            document_type='lifecycle_decision',
            source_app='tests',
            source_object_id=f'campaign:{campaign.id}',
            title='already indexed',
            text_content='existing',
        )
        self._closeout_report(campaign, requires_memory_index=True, linked_memory_document=document)

        response = self.client.post(reverse('autonomy_followup:emit', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        history = self.client.get(reverse('autonomy_followup:followups')).json()
        row = next(item for item in history if item['campaign'] == campaign.id and item['followup_type'] == 'MEMORY_INDEX')
        self.assertEqual(row['followup_status'], 'DUPLICATE_SKIPPED')

    def test_emit_memory_followup(self):
        campaign = self._campaign(title='Memory emit')
        self._closeout_report(campaign, requires_memory_index=True)

        response = self.client.post(reverse('autonomy_followup:emit', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        report = CampaignCloseoutReport.objects.get(campaign=campaign)
        self.assertIsNotNone(report.linked_memory_document_id)

    def test_emit_postmortem_followup(self):
        campaign = self._campaign(title='Postmortem emit', status='ABORTED')
        self._closeout_report(campaign, requires_postmortem=True)

        self.client.post(reverse('autonomy_followup:emit', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        report = CampaignCloseoutReport.objects.get(campaign=campaign)
        self.assertTrue(report.linked_postmortem_request)

    def test_emit_roadmap_feedback_followup(self):
        campaign = self._campaign(title='Roadmap emit')
        self._closeout_report(campaign, requires_roadmap_feedback=True)

        self.client.post(reverse('autonomy_followup:emit', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        report = CampaignCloseoutReport.objects.get(campaign=campaign)
        self.assertTrue(report.linked_feedback_artifact)

    def test_emit_blocked_when_closeout_not_ready(self):
        campaign = self._campaign(title='Blocked emit')
        self._closeout_report(campaign, closeout_status='BLOCKED', requires_memory_index=True)

        response = self.client.post(reverse('autonomy_followup:emit', kwargs={'campaign_id': campaign.id}), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_summary_endpoint(self):
        campaign = self._campaign(title='Summary campaign')
        self._closeout_report(campaign, requires_memory_index=True)
        self.client.post(reverse('autonomy_followup:run_review'), data={}, content_type='application/json')

        response = self.client.get(reverse('autonomy_followup:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())
