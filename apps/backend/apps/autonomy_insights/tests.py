from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport, CloseoutFinding
from apps.autonomy_disposition.models import CampaignDisposition
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_roadmap.services.plans import run_roadmap_plan


class AutonomyInsightsTests(TestCase):
    def _campaign(self, *, title: str, status: str, domains=None):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='insights test',
            metadata={'domains': domains or ['autonomy']},
        )
        campaign.status = status
        campaign.save(update_fields=['status', 'updated_at'])
        return campaign

    def _closeout(self, campaign, **overrides):
        defaults = {
            'disposition_type': 'CLOSED',
            'closeout_status': 'COMPLETED',
            'executive_summary': 'done',
            'lifecycle_summary': {},
            'major_blockers': [],
            'incident_summary': {},
            'intervention_summary': {},
            'recovery_summary': {},
            'final_outcome_summary': 'stable',
            'requires_postmortem': False,
            'requires_memory_index': False,
            'requires_roadmap_feedback': False,
            'closed_out_by': 'tests',
            'closed_out_at': timezone.now(),
            'metadata': {},
        }
        defaults.update(overrides)
        return CampaignCloseoutReport.objects.create(campaign=campaign, **defaults)

    def _followup_and_feedback(self, campaign, report, *, followup_type='MEMORY_INDEX', resolution_status='COMPLETED'):
        followup = CampaignFollowup.objects.create(
            campaign=campaign,
            closeout_report=report,
            followup_type=followup_type,
            followup_status='EMITTED',
            rationale='evidence',
        )
        return FollowupResolution.objects.create(
            campaign=campaign,
            followup=followup,
            resolution_status=resolution_status,
            downstream_status='COMPLETED' if resolution_status in {'COMPLETED', 'CLOSED'} else 'PENDING',
            resolution_type='MANUAL_REVIEW_REQUIRED',
            rationale='resolved',
        )

    def test_candidates_only_lifecycle_closed(self):
        closed = self._campaign(title='Closed', status='COMPLETED')
        closed_report = self._closeout(closed)
        self._followup_and_feedback(closed, closed_report)

        pending = self._campaign(title='Pending', status='COMPLETED')
        pending_report = self._closeout(pending)
        self._followup_and_feedback(pending, pending_report, resolution_status='PENDING')

        response = self.client.get(reverse('autonomy_insights:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = {row['campaign']: row for row in response.json()}
        self.assertTrue(payload[closed.id]['lifecycle_closed'])
        self.assertFalse(payload[pending.id]['lifecycle_closed'])

    def test_block_synthesis_when_followup_pending(self):
        campaign = self._campaign(title='Blocked synthesis', status='COMPLETED')
        report = self._closeout(campaign)
        self._followup_and_feedback(campaign, report, resolution_status='PENDING')

        result = self.client.post(reverse('autonomy_insights:run_review'), data={}, content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['insight_count'], 0)

    def test_generates_success_and_failure_patterns(self):
        success = self._campaign(title='Success campaign', status='COMPLETED')
        success_report = self._closeout(success)
        CloseoutFinding.objects.create(closeout_report=success_report, finding_type='success_factor', summary='Strong preflight checks')
        self._followup_and_feedback(success, success_report)

        failure = self._campaign(title='Failure campaign', status='ABORTED')
        failure_report = self._closeout(failure, disposition_type='ABORTED', requires_roadmap_feedback=True)
        CampaignDisposition.objects.create(campaign=failure, disposition_type='ABORTED', disposition_status='APPLIED', rationale='abort')
        CloseoutFinding.objects.create(closeout_report=failure_report, finding_type='failure_mode', summary='Approval timeout loops')
        self._followup_and_feedback(failure, failure_report, followup_type='POSTMORTEM_REQUEST')

        self.client.post(reverse('autonomy_insights:run_review'), data={}, content_type='application/json')
        insights = self.client.get(reverse('autonomy_insights:insights')).json()
        insight_types = {row['insight_type'] for row in insights}
        self.assertIn('success_pattern', insight_types)
        self.assertIn('failure_pattern', insight_types)

    def test_generates_blocker_and_governance_patterns_and_summary(self):
        first = self._campaign(title='Blocker one', status='ABORTED', domains=['execution'])
        first_report = self._closeout(first, disposition_type='ABORTED', requires_roadmap_feedback=True)
        CampaignDisposition.objects.create(campaign=first, disposition_type='ABORTED', disposition_status='APPLIED', rationale='abort one')
        CloseoutFinding.objects.create(closeout_report=first_report, finding_type='failure_mode', summary='Approval backlog')
        CloseoutFinding.objects.create(closeout_report=first_report, finding_type='approval_friction', summary='High approval friction')
        self._followup_and_feedback(first, first_report, followup_type='POSTMORTEM_REQUEST')

        second = self._campaign(title='Blocker two', status='ABORTED', domains=['execution'])
        second_report = self._closeout(second, disposition_type='ABORTED', requires_roadmap_feedback=True)
        CampaignDisposition.objects.create(campaign=second, disposition_type='ABORTED', disposition_status='APPLIED', rationale='abort two')
        CloseoutFinding.objects.create(closeout_report=second_report, finding_type='failure_mode', summary='Approval backlog')
        CloseoutFinding.objects.create(closeout_report=second_report, finding_type='approval_friction', summary='High approval friction')
        self._followup_and_feedback(second, second_report, followup_type='POSTMORTEM_REQUEST')

        self.client.post(reverse('autonomy_insights:run_review'), data={}, content_type='application/json')
        summary = self.client.get(reverse('autonomy_insights:summary')).json()
        self.assertGreaterEqual(summary['blocker_pattern_count'], 1)
        self.assertGreaterEqual(summary['governance_pattern_count'], 1)
        self.assertTrue(summary['recommendation_summary'])

    def test_summary_endpoint_works(self):
        response = self.client.get(reverse('autonomy_insights:summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('candidate_count', response.json())
