from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.champion_challenger.models import StackProfileBinding
from apps.champion_challenger.services.bindings import get_or_create_champion_binding
from apps.markets.models import Market, MarketSourceType, MarketStatus, Provider
from apps.mission_control.services.cycle_runner import run_mission_control_cycle
from apps.mission_control.models import MissionControlSession, MissionControlSessionStatus
from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutRunStatus
from apps.rollout_manager.services import evaluate_guardrails, get_current_rollout_run, route_opportunity


class RolloutManagerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.champion = get_or_create_champion_binding()
        self.candidate = StackProfileBinding.objects.create(name='candidate_rollout_v1', is_champion=False, execution_profile='conservative_paper')

    def _create_market(self):
        provider = Provider.objects.create(name='Kalshi', slug='kalshi', is_active=True)
        return Market.objects.create(
            provider=provider,
            title='Rollout test market',
            slug='rollout-test-market',
            source_type=MarketSourceType.REAL_READ_ONLY,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('55'),
            current_no_price=Decimal('45'),
        )

    def test_create_plan_and_lifecycle_endpoints(self):
        plan_response = self.client.post(
            reverse('rollout_manager:create-plan'),
            {'candidate_binding_id': self.candidate.id, 'mode': 'CANARY', 'canary_percentage': 25},
            format='json',
        )
        self.assertEqual(plan_response.status_code, 201)
        plan_id = plan_response.json()['id']

        start_response = self.client.post(reverse('rollout_manager:start', args=[plan_id]), {'metadata': {'initiated_by': 'test'}}, format='json')
        self.assertEqual(start_response.status_code, 201)
        run_id = start_response.json()['id']

        pause_response = self.client.post(reverse('rollout_manager:pause', args=[run_id]), {}, format='json')
        self.assertEqual(pause_response.status_code, 200)
        self.assertEqual(pause_response.json()['status'], 'PAUSED')

        resume_response = self.client.post(reverse('rollout_manager:resume', args=[run_id]), {}, format='json')
        self.assertEqual(resume_response.status_code, 200)
        self.assertEqual(resume_response.json()['status'], 'RUNNING')

        rollback_response = self.client.post(
            reverse('rollout_manager:rollback', args=[run_id]),
            {'reason': 'manual rollback in test'},
            format='json',
        )
        self.assertEqual(rollback_response.status_code, 200)
        self.assertEqual(rollback_response.json()['status'], 'ROLLED_BACK')

    def test_deterministic_canary_routing(self):
        plan_response = self.client.post(
            reverse('rollout_manager:create-plan'),
            {'candidate_binding_id': self.candidate.id, 'mode': 'CANARY', 'canary_percentage': 35},
            format='json',
        )
        run_response = self.client.post(reverse('rollout_manager:start', args=[plan_response.json()['id']]), {}, format='json')
        run_id = run_response.json()['id']
        run = get_current_rollout_run()
        self.assertIsNotNone(run)
        market = self._create_market()

        first = route_opportunity(run=run, market_id=market.id, profile_slug='balanced')
        second = route_opportunity(run=run, market_id=market.id, profile_slug='balanced')
        self.assertEqual(first.route, second.route)
        self.assertEqual(first.bucket, second.bucket)
        self.assertEqual(run_id, run.id)

    def test_guardrail_trigger(self):
        plan_response = self.client.post(reverse('rollout_manager:create-plan'), {'candidate_binding_id': self.candidate.id}, format='json')
        self.client.post(reverse('rollout_manager:start', args=[plan_response.json()['id']]), {}, format='json')
        run = get_current_rollout_run()
        self.assertIsNotNone(run)

        events = evaluate_guardrails(
            run=run,
            metrics={
                'fill_rate_delta': -0.2,
                'execution_adjusted_pnl_delta': -25,
                'no_fill_rate_delta': 0.3,
                'queue_pressure_delta': 0.4,
                'drawdown_delta': 0.1,
            },
        )
        self.assertGreaterEqual(len(events), 2)
        self.assertTrue(RolloutGuardrailEvent.objects.filter(run=run).exists())

    def test_current_rollout_endpoint(self):
        plan_response = self.client.post(reverse('rollout_manager:create-plan'), {'candidate_binding_id': self.candidate.id}, format='json')
        self.client.post(reverse('rollout_manager:start', args=[plan_response.json()['id']]), {}, format='json')

        response = self.client.get(reverse('rollout_manager:current'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()['current_rollout'])

    def test_mission_control_integration_with_rollout(self):
        market = self._create_market()
        plan_response = self.client.post(reverse('rollout_manager:create-plan'), {'candidate_binding_id': self.candidate.id, 'canary_percentage': 50}, format='json')
        self.client.post(reverse('rollout_manager:start', args=[plan_response.json()['id']]), {}, format='json')

        session = MissionControlSession.objects.create(
            status=MissionControlSessionStatus.RUNNING,
            summary='rollout integration test',
            metadata={'slug': 'balanced_mission_control', 'cycle_interval_seconds': 60},
        )
        cycle = run_mission_control_cycle(session=session, settings=session.metadata)
        cycle.refresh_from_db()

        self.assertIn('rollout', cycle.details)
        run = get_current_rollout_run()
        self.assertIsNotNone(run)
        run.refresh_from_db()
        self.assertIn(run.status, {StackRolloutRunStatus.RUNNING, StackRolloutRunStatus.PAUSED, StackRolloutRunStatus.ROLLED_BACK, StackRolloutRunStatus.COMPLETED})
