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


class AutonomyBacklogTests(TestCase):
    def _campaign(self, *, title='Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='autonomy backlog test',
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

    def _adopted_artifact(self, *, target='roadmap'):
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
        emit_response = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json')
        artifact_id = emit_response.json()['artifact_id']
        self.client.post(reverse('autonomy_advisory_resolution:adopt', args=[artifact_id]), data={}, content_type='application/json')
        return artifact_id

    def test_candidates_include_adopted(self):
        self._adopted_artifact(target='roadmap')
        response = self.client.get(reverse('autonomy_backlog:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        self.assertTrue(any(row['resolution_status'] == 'ADOPTED' for row in payload))

    def test_run_review_creates_no_duplicates(self):
        artifact_id = self._adopted_artifact(target='scenario')
        self.client.post(reverse('autonomy_backlog:run_review'), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_backlog:run_review'), data={}, content_type='application/json')
        self.assertEqual(GovernanceBacklogItem.objects.filter(advisory_artifact_id=artifact_id).count(), 1)

    def test_creation_sets_backlog_type_by_target(self):
        roadmap_artifact = self._adopted_artifact(target='roadmap')
        scenario_artifact = self._adopted_artifact(target='scenario')
        self.client.post(reverse('autonomy_backlog:create', args=[roadmap_artifact]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_backlog:create', args=[scenario_artifact]), data={}, content_type='application/json')

        roadmap_item = GovernanceBacklogItem.objects.get(advisory_artifact_id=roadmap_artifact)
        scenario_item = GovernanceBacklogItem.objects.get(advisory_artifact_id=scenario_artifact)
        self.assertEqual(roadmap_item.backlog_type, 'ROADMAP_CHANGE_CANDIDATE')
        self.assertEqual(scenario_item.backlog_type, 'SCENARIO_CAUTION_CANDIDATE')

    def test_prioritize_action_is_audited(self):
        artifact_id = self._adopted_artifact(target='program')
        create_response = self.client.post(reverse('autonomy_backlog:create', args=[artifact_id]), data={}, content_type='application/json')
        item_id = create_response.json()['item_id']
        response = self.client.post(reverse('autonomy_backlog:prioritize', args=[item_id]), data={'actor': 'test-operator'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        item = GovernanceBacklogItem.objects.get(pk=item_id)
        self.assertEqual(item.backlog_status, 'PRIORITIZED')
        self.assertEqual(item.metadata.get('prioritized_by'), 'test-operator')

    def test_manual_review_when_missing_data(self):
        artifact_id = self._adopted_artifact(target='memory')
        run = self.client.post(reverse('autonomy_backlog:run_review'), data={}, content_type='application/json')
        self.assertEqual(run.status_code, 200)

        recommendations = self.client.get(reverse('autonomy_backlog:recommendations')).json()
        advisory_recommendations = [row for row in recommendations if row['advisory_artifact'] == artifact_id]
        self.assertTrue(any(row['recommendation_type'] == 'REQUIRE_MANUAL_BACKLOG_REVIEW' for row in advisory_recommendations))

    def test_summary_endpoint(self):
        self._adopted_artifact(target='manager')
        self.client.post(reverse('autonomy_backlog:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_backlog:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
