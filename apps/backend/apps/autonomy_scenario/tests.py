from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.autonomy_manager.models import AutonomyDomainStatus, AutonomyStageState
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus
from apps.autonomy_rollout.services.baseline import create_baseline_snapshot
from apps.autonomy_scenario.services.options import build_scenario_option_drafts
from apps.autonomy_scenario.services.simulation import collect_scenario_evidence


class AutonomyScenarioTests(TestCase):
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

    def test_scenario_option_build_basic(self):
        dependencies = []
        evidence = collect_scenario_evidence()
        options = build_scenario_option_drafts(evidence=evidence, dependencies=dependencies)
        self.assertTrue(options)
        self.assertTrue(any(option.option_type == 'PROMOTE_SINGLE_DOMAIN' for option in options))

    def test_dependency_conflict_detection_generates_do_not_execute(self):
        state = AutonomyStageState.objects.get(domain__slug='incident_response')
        state.status = AutonomyDomainStatus.DEGRADED
        state.save(update_fields=['status', 'updated_at'])

        run = self.client.post(reverse('autonomy_scenario:run'), data={}, content_type='application/json')
        self.assertEqual(run.status_code, 201)
        recommendations = self.client.get(reverse('autonomy_scenario:recommendations')).json()
        self.assertTrue(any(item['recommendation_code'] == 'DO_NOT_EXECUTE' for item in recommendations))

    def test_risky_bundle_detection(self):
        run = self.client.post(reverse('autonomy_scenario:run'), data={}, content_type='application/json').json()
        options_by_id = {item['id']: item for item in run['options']}
        bundle_risks = [risk for risk in run['risk_estimates'] if options_by_id.get(risk['option'], {}).get('is_bundle')]
        self.assertTrue(bundle_risks)

    def test_best_next_move_recommendation_exists(self):
        self.client.post(reverse('autonomy_scenario:run'), data={}, content_type='application/json')
        recommendations = self.client.get(reverse('autonomy_scenario:recommendations')).json()
        self.assertTrue(any(item['recommendation_code'] == 'BEST_NEXT_MOVE' for item in recommendations))

    def test_do_not_execute_when_blocked(self):
        self._create_rollout_warning('runbook_remediation', AutonomyRolloutStatus.ROLLBACK_RECOMMENDED)
        run = self.client.post(reverse('autonomy_scenario:run'), data={}, content_type='application/json').json()
        do_not = [item for item in run['recommendations'] if item['recommendation_code'] == 'DO_NOT_EXECUTE']
        self.assertTrue(do_not)

    def test_core_endpoints_work(self):
        run = self.client.post(reverse('autonomy_scenario:run'), data={'requested_by': 'tests'}, content_type='application/json')
        self.assertEqual(run.status_code, 201)
        run_id = run.json()['id']
        urls = [
            reverse('autonomy_scenario:runs'),
            reverse('autonomy_scenario:run-detail', args=[run_id]),
            reverse('autonomy_scenario:options'),
            reverse('autonomy_scenario:recommendations'),
            reverse('autonomy_scenario:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
