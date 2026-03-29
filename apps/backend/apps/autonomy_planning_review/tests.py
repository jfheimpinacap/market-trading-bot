from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_insights.models import CampaignInsight
from apps.autonomy_roadmap.services.plans import run_roadmap_plan


class AutonomyPlanningReviewTests(TestCase):
    def _campaign(self, *, title='Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='planning review test',
            metadata={'domains': ['autonomy']},
        )
        campaign.status = 'COMPLETED'
        campaign.save(update_fields=['status', 'updated_at'])

        report = CampaignCloseoutReport.objects.create(
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
            requires_postmortem=False,
            requires_memory_index=False,
            requires_roadmap_feedback=False,
            closed_out_by='tests',
            closed_out_at=timezone.now(),
            metadata={},
        )
        followup = CampaignFollowup.objects.create(
            campaign=campaign,
            closeout_report=report,
            followup_type='MEMORY_INDEX',
            followup_status='EMITTED',
            rationale='emit',
        )
        FollowupResolution.objects.create(
            campaign=campaign,
            followup=followup,
            resolution_status='COMPLETED',
            downstream_status='COMPLETED',
            resolution_type='MANUAL_REVIEW_REQUIRED',
            rationale='resolved',
        )
        return campaign

    def _emit_proposal(self, *, target='roadmap'):
        campaign = self._campaign(title=f'Campaign {target}')
        insight = CampaignInsight.objects.create(
            campaign=campaign,
            insight_type='success_pattern',
            scope='campaign',
            summary=f'Insight for {target}',
            evidence_summary={},
            reason_codes=['test_reason'],
            recommended_followup='Manual note recommended',
            recommendation_target=target,
            confidence='0.8100',
            reviewed=True,
            reviewed_by='tests',
            reviewed_at=timezone.now(),
            metadata={'test': True},
        )
        emit_advisory = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json').json()
        artifact_id = emit_advisory['artifact_id']
        self.client.post(reverse('autonomy_advisory_resolution:adopt', args=[artifact_id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_backlog:create', args=[artifact_id]), data={}, content_type='application/json')
        backlog_item = GovernanceBacklogItem.objects.get(advisory_artifact_id=artifact_id)
        backlog_item.backlog_status = 'PRIORITIZED'
        backlog_item.save(update_fields=['backlog_status', 'updated_at'])
        emit_proposal = self.client.post(reverse('autonomy_intake:emit', args=[backlog_item.id]), data={}, content_type='application/json').json()
        return emit_proposal['proposal_id']

    def test_candidates_only_include_emitted_ready_ack_or_blocked(self):
        self._emit_proposal(target='roadmap')
        response = self.client.get(reverse('autonomy_planning_review:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        self.assertTrue(all(row['proposal_status'] in {'EMITTED', 'READY', 'ACKNOWLEDGED', 'BLOCKED'} for row in payload))

    def test_acknowledge_action_is_audited(self):
        proposal_id = self._emit_proposal(target='scenario')
        response = self.client.post(reverse('autonomy_planning_review:acknowledge', args=[proposal_id]), data={'actor': 'test-operator'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['resolution_status'], 'ACKNOWLEDGED')

    def test_accept_action_is_audited(self):
        proposal_id = self._emit_proposal(target='program')
        response = self.client.post(reverse('autonomy_planning_review:accept', args=[proposal_id]), data={'actor': 'test-operator'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['resolution_status'], 'ACCEPTED')

    def test_run_review_does_not_override_accepted(self):
        proposal_id = self._emit_proposal(target='manager')
        self.client.post(reverse('autonomy_planning_review:accept', args=[proposal_id]), data={}, content_type='application/json')
        run_response = self.client.post(reverse('autonomy_planning_review:run_review'), data={}, content_type='application/json')
        self.assertEqual(run_response.status_code, 200)

        resolutions = self.client.get(reverse('autonomy_planning_review:resolutions')).json()
        row = next(item for item in resolutions if item['planning_proposal'] == proposal_id)
        self.assertEqual(row['resolution_status'], 'ACCEPTED')

    def test_summary_endpoint(self):
        self._emit_proposal(target='operator_review')
        self.client.post(reverse('autonomy_planning_review:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_planning_review:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
