from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.continuous_demo.models import ContinuousDemoSession, SessionStatus
from apps.continuous_demo.services.cycle import run_single_cycle
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.proposal_engine.services import generate_trade_proposal
from apps.safety_guard.models import SafetyEvent, SafetyPolicyConfig, SafetyStatus
from apps.safety_guard.services import disable_kill_switch, enable_kill_switch, evaluate_auto_execution, evaluate_cycle_health
from apps.semi_auto_demo.services import run_scan_and_execute
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class SafetyGuardServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_exposure_limit_blocks_auto_execution(self):
        config = SafetyPolicyConfig.objects.create(name='local', max_position_value_per_market=Decimal('10.00'))
        proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='automation')
        proposal.suggested_quantity = Decimal('100.0000')
        proposal.suggested_side = 'YES'
        proposal.suggested_trade_type = 'BUY'
        proposal.is_actionable = True
        proposal.save(update_fields=['suggested_quantity', 'suggested_side', 'suggested_trade_type', 'is_actionable', 'updated_at'])

        decision = evaluate_auto_execution(proposal=proposal, auto_trades_so_far=0)

        self.assertFalse(decision.allowed)
        self.assertIn('exposure', ' '.join(decision.reasons).lower())

    def test_drawdown_limit_triggers_hard_stop(self):
        config = SafetyPolicyConfig.objects.create(name='drawdown', max_daily_or_session_drawdown=Decimal('100.00'))
        self.account.equity = self.account.initial_balance - Decimal('150.00')
        self.account.unrealized_pnl = Decimal('-150.00')
        self.account.save(update_fields=['equity', 'unrealized_pnl', 'updated_at'])

        proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='automation')
        proposal.suggested_quantity = Decimal('1.0000')
        proposal.suggested_side = 'YES'
        proposal.suggested_trade_type = 'BUY'
        proposal.is_actionable = True
        proposal.save(update_fields=['suggested_quantity', 'suggested_side', 'suggested_trade_type', 'is_actionable', 'updated_at'])

        decision = evaluate_auto_execution(proposal=proposal, auto_trades_so_far=0)
        config.refresh_from_db()

        self.assertFalse(decision.allowed)
        self.assertTrue(config.hard_stop_active)
        self.assertEqual(config.status, SafetyStatus.HARD_STOP)

    def test_kill_switch_enable_disable(self):
        config = enable_kill_switch()
        self.assertTrue(config.kill_switch_enabled)

        config = disable_kill_switch()
        self.assertFalse(config.kill_switch_enabled)

    def test_cooldown_triggered_after_repeated_blocked_cycles(self):
        config = SafetyPolicyConfig.objects.create(name='cooldown', cooldown_after_block_count=1)
        session = ContinuousDemoSession.objects.create(session_status=SessionStatus.RUNNING)
        cycle = run_single_cycle(session=session, settings={'max_auto_trades_per_cycle': 0, 'market_limit_per_cycle': 2, 'market_scope': 'mixed', 'review_after_trade': False, 'revalue_after_trade': False})
        cycle.blocked_count = 1
        cycle.save(update_fields=['blocked_count', 'updated_at'])

        evaluate_cycle_health(cycle=cycle)
        config.refresh_from_db()

        self.assertEqual(config.status, SafetyStatus.COOLDOWN)


class SafetyGuardApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        ensure_demo_account()
        self.client = APIClient()

    def test_main_endpoints_operational(self):
        self.assertEqual(self.client.get(reverse('safety_guard:status')).status_code, 200)
        self.assertEqual(self.client.get(reverse('safety_guard:events')).status_code, 200)
        self.assertEqual(self.client.post(reverse('safety_guard:kill-switch-enable'), {}, format='json').status_code, 200)
        self.assertEqual(self.client.post(reverse('safety_guard:kill-switch-disable'), {}, format='json').status_code, 200)

    def test_loop_blocked_by_kill_switch(self):
        self.client.post(reverse('safety_guard:kill-switch-enable'), {}, format='json')
        response = self.client.post(reverse('continuous_demo:start'), {'cycle_interval_seconds': 2}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_semi_auto_blocked_by_kill_switch(self):
        self.client.post(reverse('safety_guard:kill-switch-enable'), {}, format='json')
        response = self.client.post(reverse('semi_auto_demo:run'), {}, format='json')
        self.assertEqual(response.status_code, 409)
