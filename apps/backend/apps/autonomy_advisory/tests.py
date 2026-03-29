from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_campaign.services import create_campaign
from apps.autonomy_closeout.models import CampaignCloseoutReport
from apps.autonomy_feedback.models import FollowupResolution
from apps.autonomy_followup.models import CampaignFollowup
from apps.autonomy_insights.models import CampaignInsight
from apps.autonomy_roadmap.services.plans import run_roadmap_plan


class AutonomyAdvisoryTests(TestCase):
    def _campaign(self, *, title='Campaign'):
        plan = run_roadmap_plan(requested_by='tests')
        campaign = create_campaign(
            source_type='roadmap_plan',
            source_object_id=str(plan.id),
            title=title,
            summary='advisory test',
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

    def _insight(self, *, target='memory', reviewed=True):
        campaign = self._campaign(title=f'Campaign {target}')
        return CampaignInsight.objects.create(
            campaign=campaign,
            insight_type='success_pattern',
            scope='campaign',
            summary=f'Insight for {target}',
            evidence_summary={},
            reason_codes=['test_reason'],
            recommended_followup='Manual note recommended',
            recommendation_target=target,
            confidence='0.8200',
            reviewed=reviewed,
            reviewed_by='tests' if reviewed else '',
            reviewed_at=timezone.now() if reviewed else None,
            metadata={'test': True},
        )

    def test_candidates_ready_selection(self):
        ready = self._insight(target='memory', reviewed=True)
        blocked = self._insight(target='roadmap', reviewed=False)

        response = self.client.get(reverse('autonomy_advisory:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = {row['insight']: row for row in response.json()}
        self.assertTrue(payload[ready.id]['ready_for_emission'])
        self.assertFalse(payload[blocked.id]['ready_for_emission'])

    def test_emit_memory_precedent_note(self):
        insight = self._insight(target='memory', reviewed=True)
        response = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        artifacts = self.client.get(reverse('autonomy_advisory:artifacts')).json()
        artifact = next(row for row in artifacts if row['insight'] == insight.id)
        self.assertEqual(artifact['artifact_type'], 'MEMORY_PRECEDENT_NOTE')
        self.assertEqual(artifact['artifact_status'], 'EMITTED')
        self.assertIsNotNone(artifact['linked_memory_document'])

    def test_emit_roadmap_and_scenario_notes(self):
        roadmap = self._insight(target='roadmap', reviewed=True)
        scenario = self._insight(target='scenario', reviewed=True)
        self.client.post(reverse('autonomy_advisory:emit_insight', args=[roadmap.id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_advisory:emit_insight', args=[scenario.id]), data={}, content_type='application/json')
        artifacts = self.client.get(reverse('autonomy_advisory:artifacts')).json()
        by_insight = {row['insight']: row for row in artifacts}
        self.assertEqual(by_insight[roadmap.id]['artifact_type'], 'ROADMAP_GOVERNANCE_NOTE')
        self.assertEqual(by_insight[scenario.id]['artifact_type'], 'SCENARIO_CAUTION_NOTE')

    def test_blocked_when_not_reviewed(self):
        insight = self._insight(target='program', reviewed=False)
        response = self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        artifacts = self.client.get(reverse('autonomy_advisory:artifacts')).json()
        artifact = next(row for row in artifacts if row['insight'] == insight.id)
        self.assertEqual(artifact['artifact_status'], 'BLOCKED')

    def test_dedup_duplicate_skipped(self):
        insight = self._insight(target='memory', reviewed=True)
        self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_advisory:emit_insight', args=[insight.id]), data={}, content_type='application/json')
        artifacts = [row for row in self.client.get(reverse('autonomy_advisory:artifacts')).json() if row['insight'] == insight.id]
        statuses = {row['artifact_status'] for row in artifacts}
        self.assertIn('EMITTED', statuses)
        self.assertIn('DUPLICATE_SKIPPED', statuses)

    def test_run_review_and_summary_endpoint(self):
        self._insight(target='memory', reviewed=True)
        self._insight(target='program', reviewed=True)
        self._insight(target='manager', reviewed=False)

        run_response = self.client.post(reverse('autonomy_advisory:run_review'), data={}, content_type='application/json')
        self.assertEqual(run_response.status_code, 200)
        payload = run_response.json()
        self.assertGreaterEqual(payload['candidate_count'], 3)

        summary_response = self.client.get(reverse('autonomy_advisory:summary'))
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertIn('candidate_count', summary)
        self.assertIn('recommendation_summary', summary)
