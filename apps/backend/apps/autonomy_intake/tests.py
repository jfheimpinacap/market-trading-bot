from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_insights.models import CampaignInsight
from apps.autonomy_roadmap.services.plans import run_roadmap_plan
from apps.autonomy_backlog.models import GovernanceBacklogItem
from apps.autonomy_intake.models import PlanningProposal


class AutonomyIntakeTests(TestCase):
    def _campaign(self, *, title='Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='autonomy intake test',
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
            followup_type='ROADMAP_FEEDBACK',
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

    def _prioritized_backlog_item(self, *, target='roadmap'):
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
            confidence='0.9200',
            reviewed=True,
            reviewed_by='tests',
            reviewed_at=timezone.now(),
            metadata={'test': True},
        )
        artifact_id = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json').json()['artifact_id']
        self.client.post(reverse('autonomy_advisory_resolution:adopt', args=[artifact_id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_backlog:create', args=[artifact_id]), data={}, content_type='application/json')
        item = GovernanceBacklogItem.objects.get(advisory_artifact_id=artifact_id)
        item.backlog_status = 'PRIORITIZED'
        item.save(update_fields=['backlog_status', 'updated_at'])
        return item

    def test_candidates_include_ready_or_prioritized_backlog_items(self):
        item = self._prioritized_backlog_item(target='roadmap')
        response = self.client.get(reverse('autonomy_intake:candidates'))
        self.assertEqual(response.status_code, 200)
        row = next(x for x in response.json() if x['backlog_item'] == item.id)
        self.assertTrue(row['ready_for_intake'])

    def test_run_review_dedups_emitted_proposals(self):
        item = self._prioritized_backlog_item(target='scenario')
        self.client.post(reverse('autonomy_intake:run_review'), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_intake:run_review'), data={}, content_type='application/json')
        self.assertEqual(PlanningProposal.objects.filter(backlog_item_id=item.id).count(), 1)

    def test_emission_maps_core_proposal_types(self):
        roadmap_item = self._prioritized_backlog_item(target='roadmap')
        scenario_item = self._prioritized_backlog_item(target='scenario')
        program_item = self._prioritized_backlog_item(target='program')

        self.client.post(reverse('autonomy_intake:emit', args=[roadmap_item.id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_intake:emit', args=[scenario_item.id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_intake:emit', args=[program_item.id]), data={}, content_type='application/json')

        self.assertEqual(PlanningProposal.objects.get(backlog_item=roadmap_item).proposal_type, 'ROADMAP_PROPOSAL')
        self.assertEqual(PlanningProposal.objects.get(backlog_item=scenario_item).proposal_type, 'SCENARIO_PROPOSAL')
        self.assertEqual(PlanningProposal.objects.get(backlog_item=program_item).proposal_type, 'PROGRAM_REVIEW_PROPOSAL')

    def test_manual_review_recommendation_when_backlog_not_ready(self):
        item = self._prioritized_backlog_item(target='manager')
        item.backlog_status = 'DEFERRED'
        item.rationale = ''
        item.save(update_fields=['backlog_status', 'rationale', 'updated_at'])

        self.client.post(reverse('autonomy_intake:run_review'), data={}, content_type='application/json')
        recommendations = self.client.get(reverse('autonomy_intake:recommendations')).json()
        related = [row for row in recommendations if row['backlog_item'] == item.id]
        self.assertTrue(any(row['recommendation_type'] == 'REQUIRE_MANUAL_INTAKE_REVIEW' for row in related))

    def test_summary_endpoint(self):
        item = self._prioritized_backlog_item(target='roadmap')
        self.client.post(reverse('autonomy_intake:emit', args=[item.id]), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_intake:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
        self.assertIn('total_proposals', payload)
