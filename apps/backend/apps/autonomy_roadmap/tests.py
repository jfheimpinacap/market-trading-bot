from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_manager.models import AutonomyDomainStatus, AutonomyStageState
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus
from apps.autonomy_rollout.services.baseline import create_baseline_snapshot


class AutonomyRoadmapTests(TestCase):
    def setUp(self):
        sync_domain_catalog()

    def _create_rollout_warning(self, domain_slug: str, status: str):
        domain_state = AutonomyStageState.objects.select_related('domain').get(domain__slug=domain_slug)
        transition = domain_state.transitions.order_by('-created_at', '-id').first()
        if not transition:
            from apps.autonomy_manager.models import AutonomyStageTransition

            transition = AutonomyStageTransition.objects.create(
                domain=domain_state.domain,
                state=domain_state,
                previous_stage=domain_state.current_stage,
                requested_stage=domain_state.current_stage,
                applied_stage=domain_state.current_stage,
                status='APPLIED',
                rationale='seed transition',
                applied_at=timezone.now(),
            )
        run = AutonomyRolloutRun.objects.create(
            autonomy_stage_transition=transition,
            domain=domain_state.domain,
            rollout_status=status,
            summary='seed rollout warning',
        )
        create_baseline_snapshot(run)

    def test_dependency_mapping_seeded(self):
        response = self.client.get(reverse('autonomy_roadmap:dependencies'))
        self.assertEqual(response.status_code, 200)
        items = response.json()
        pairs = {(i['source_domain_slug'], i['target_domain_slug'], i['dependency_type']) for i in items}
        self.assertIn(('runbook_remediation', 'incident_response', 'requires_stable'), pairs)
        self.assertIn(('profile_governance_actions', 'portfolio_governance_actions', 'incompatible_parallel'), pairs)

    def test_freeze_when_domain_is_degraded(self):
        state = AutonomyStageState.objects.get(domain__slug='incident_response')
        state.status = AutonomyDomainStatus.DEGRADED
        state.save(update_fields=['status', 'updated_at'])

        plan = self.client.post(reverse('autonomy_roadmap:run-plan'), data={}, content_type='application/json')
        self.assertEqual(plan.status_code, 201)
        recommendations = self.client.get(reverse('autonomy_roadmap:recommendations')).json()
        freeze = [r for r in recommendations if r['domain_slug'] == 'incident_response' and r['action'] == 'FREEZE_DOMAIN']
        self.assertTrue(freeze)

    def test_incompatible_parallel_detection(self):
        self.client.post(reverse('autonomy_roadmap:run-plan'), data={}, content_type='application/json')
        recommendations = self.client.get(reverse('autonomy_roadmap:recommendations')).json()
        conflict = [
            r
            for r in recommendations
            if r['domain_slug'] == 'profile_governance_actions' and r['action'] == 'DO_NOT_PROMOTE_IN_PARALLEL'
        ]
        self.assertTrue(conflict)

    def test_sequence_recommendation_and_summary_endpoint(self):
        self._create_rollout_warning('incident_response', AutonomyRolloutStatus.OBSERVING)
        run_response = self.client.post(reverse('autonomy_roadmap:run-plan'), data={'requested_by': 'tests'}, content_type='application/json')
        self.assertEqual(run_response.status_code, 201)
        payload = run_response.json()
        self.assertIn('incident_response', payload['blocked_domains'])

        summary = self.client.get(reverse('autonomy_roadmap:summary'))
        self.assertEqual(summary.status_code, 200)
        summary_payload = summary.json()
        self.assertGreaterEqual(summary_payload['total_plans'], 1)
        self.assertIsNotNone(summary_payload['latest_plan'])

    def test_core_endpoints_work(self):
        run = self.client.post(reverse('autonomy_roadmap:run-plan'), data={}, content_type='application/json')
        self.assertEqual(run.status_code, 201)
        plan_id = run.json()['id']

        urls = [
            reverse('autonomy_roadmap:dependencies'),
            reverse('autonomy_roadmap:plans'),
            reverse('autonomy_roadmap:plan-detail', args=[plan_id]),
            reverse('autonomy_roadmap:recommendations'),
            reverse('autonomy_roadmap:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
