from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_insights.models import CampaignInsight
from apps.autonomy_intake.models import PlanningProposal
from apps.autonomy_roadmap.services.plans import run_roadmap_plan


class AutonomyDecisionTests(TestCase):
    def _emit_accepted_proposal(self, *, target='roadmap') -> int:
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=f'Decision Campaign {target}',
            summary='decision test',
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
        followup = CampaignFollowup.objects.create(campaign=campaign, closeout_report=report, followup_type='MEMORY_INDEX', followup_status='EMITTED', rationale='emit')
        FollowupResolution.objects.create(campaign=campaign, followup=followup, resolution_status='COMPLETED', downstream_status='COMPLETED', resolution_type='MANUAL_REVIEW_REQUIRED', rationale='resolved')

        insight = CampaignInsight.objects.create(
            campaign=campaign,
            insight_type='success_pattern',
            scope='campaign',
            summary=f'Insight for {target}',
            evidence_summary={},
            reason_codes=['test'],
            recommended_followup='manual',
            recommendation_target=target,
            confidence='0.8400',
            reviewed=True,
            reviewed_by='tests',
            reviewed_at=timezone.now(),
            metadata={'test': True},
        )
        artifact_id = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json').json()['artifact_id']
        self.client.post(reverse('autonomy_advisory_resolution:adopt', args=[artifact_id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_backlog:create', args=[artifact_id]), data={}, content_type='application/json')

        backlog_item = GovernanceBacklogItem.objects.get(advisory_artifact_id=artifact_id)
        backlog_item.backlog_status = 'PRIORITIZED'
        backlog_item.save(update_fields=['backlog_status', 'updated_at'])

        proposal_id = self.client.post(reverse('autonomy_intake:emit', args=[backlog_item.id]), data={}, content_type='application/json').json()['proposal_id']
        self.client.post(reverse('autonomy_planning_review:accept', args=[proposal_id]), data={}, content_type='application/json')
        return proposal_id

    def test_candidates_include_accepted_only(self):
        self._emit_accepted_proposal(target='roadmap')
        response = self.client.get(reverse('autonomy_decision:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        for row in payload:
            self.assertTrue(row['ready_for_decision'] or row['blockers'] or row['existing_decision'])

    def test_register_creates_roadmap_scenario_program_types(self):
        roadmap = self._emit_accepted_proposal(target='roadmap')
        scenario = self._emit_accepted_proposal(target='scenario')
        program = self._emit_accepted_proposal(target='program')

        self.client.post(reverse('autonomy_decision:register', args=[roadmap]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_decision:register', args=[scenario]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_decision:register', args=[program]), data={}, content_type='application/json')

        decisions = self.client.get(reverse('autonomy_decision:decisions')).json()
        decision_types = {item['decision_type'] for item in decisions}
        self.assertIn('ROADMAP_DECISION_PACKAGE', decision_types)
        self.assertIn('SCENARIO_DECISION_PACKAGE', decision_types)
        self.assertIn('PROGRAM_DECISION_PACKAGE', decision_types)

    def test_duplicate_registration_is_skipped(self):
        proposal_id = self._emit_accepted_proposal(target='roadmap')
        first = self.client.post(reverse('autonomy_decision:register', args=[proposal_id]), data={}, content_type='application/json')
        second = self.client.post(reverse('autonomy_decision:register', args=[proposal_id]), data={}, content_type='application/json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['decision_status'], 'DUPLICATE_SKIPPED')

    def test_register_requires_accepted_status(self):
        proposal_id = self._emit_accepted_proposal(target='manager')
        proposal = PlanningProposal.objects.get(pk=proposal_id)
        proposal.planning_resolution.resolution_status = 'DEFERRED'
        proposal.planning_resolution.save(update_fields=['resolution_status', 'updated_at'])

        response = self.client.post(reverse('autonomy_decision:register', args=[proposal_id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_summary_endpoint(self):
        self._emit_accepted_proposal(target='roadmap')
        self.client.post(reverse('autonomy_decision:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_decision:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
