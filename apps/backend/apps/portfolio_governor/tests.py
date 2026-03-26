from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.opportunity_supervisor.services.execution_path import resolve_execution_path
from apps.markets.models import Market
from apps.paper_trading.models import PaperPosition, PaperPositionStatus
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.portfolio_governor.models import PortfolioThrottleState
from apps.portfolio_governor.services import run_portfolio_governance
from apps.portfolio_governor.services.throttle import build_throttle_decision_payload


class PortfolioGovernorTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.first()

    def _create_position(self, market_value: Decimal):
        PaperPosition.objects.create(
            account=self.account,
            market=self.market,
            side='YES',
            quantity=Decimal('10'),
            average_entry_price=Decimal('0.60'),
            current_mark_price=Decimal('0.61'),
            cost_basis=market_value,
            market_value=market_value,
            status=PaperPositionStatus.OPEN,
        )

    def test_exposure_snapshot_basics(self):
        self._create_position(Decimal('1200'))
        run = run_portfolio_governance()
        self.assertIsNotNone(run.exposure_snapshot)
        self.assertEqual(run.exposure_snapshot.open_positions, 1)
        self.assertGreaterEqual(run.exposure_snapshot.total_exposure, Decimal('1200'))

    def test_throttle_states(self):
        base = {
            'open_positions': 2,
            'recent_drawdown_pct': 0.01,
            'concentration_market_ratio': 0.2,
            'concentration_provider_ratio': 0.2,
            'cash_reserve_ratio': 0.4,
        }
        profile = {
            'default_max_new_positions': 3,
            'drawdown_caution_pct': 0.06,
            'drawdown_throttle_pct': 0.10,
            'drawdown_block_pct': 0.14,
            'cash_reserve_caution_ratio': 0.20,
            'cash_reserve_throttle_ratio': 0.12,
            'cash_reserve_block_ratio': 0.08,
            'max_market_concentration_ratio': 0.45,
            'max_provider_concentration_ratio': 0.55,
            'max_open_positions': 8,
            'queue_pressure_throttle': 8,
            'close_reduce_events_throttle': 5,
        }
        normal = build_throttle_decision_payload(snapshot=base, profile=profile, regime_signals=['normal'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        caution = build_throttle_decision_payload(snapshot={**base, 'recent_drawdown_pct': 0.07}, profile=profile, regime_signals=['drawdown_caution'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        throttled = build_throttle_decision_payload(snapshot={**base, 'concentration_market_ratio': 0.5}, profile=profile, regime_signals=['concentrated'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        blocked = build_throttle_decision_payload(snapshot={**base, 'recent_drawdown_pct': 0.2}, profile=profile, regime_signals=['drawdown_caution'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})

        self.assertEqual(normal['state'], PortfolioThrottleState.NORMAL)
        self.assertEqual(caution['state'], PortfolioThrottleState.CAUTION)
        self.assertEqual(throttled['state'], PortfolioThrottleState.THROTTLED)
        self.assertEqual(blocked['state'], PortfolioThrottleState.BLOCK_NEW_ENTRIES)

    def test_opportunity_path_blocked_by_portfolio_throttle(self):
        decision = resolve_execution_path(
            policy_decision='AUTO_APPROVE',
            runtime_mode='PAPER_AUTO',
            safety_status='HEALTHY',
            blocked_reasons=[],
            risk_level='LOW',
            has_allocation=True,
            portfolio_throttle_state='BLOCK_NEW_ENTRIES',
            portfolio_size_multiplier='0',
        )
        self.assertEqual(decision.path, 'BLOCKED')

    def test_api_endpoints(self):
        client = APIClient()
        run_response = client.post(reverse('portfolio_governor:run-governance'), {}, format='json')
        self.assertEqual(run_response.status_code, 200)
        run_id = run_response.json()['id']

        self.assertEqual(client.get(reverse('portfolio_governor:run-list')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:run-detail', kwargs={'pk': run_id})).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:throttle')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:summary')).status_code, 200)
