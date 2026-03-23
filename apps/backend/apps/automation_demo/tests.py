from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.automation_demo.models import DemoAutomationRun
from apps.automation_demo.services import execute_demo_action, run_demo_cycle
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market, MarketSnapshot
from apps.paper_trading.models import PaperPortfolioSnapshot
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.postmortem_demo.models import TradeReview
from apps.signals.models import MarketSignal


class DemoAutomationServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5'), account=self.account)

    def test_execute_simulate_tick_records_successful_run(self):
        before = MarketSnapshot.objects.count()

        run = execute_demo_action(action_type=DemoAutomationRun.ActionType.SIMULATE_TICK)

        self.assertEqual(run.status, DemoAutomationRun.Status.SUCCESS)
        self.assertEqual(run.action_type, DemoAutomationRun.ActionType.SIMULATE_TICK)
        self.assertGreater(MarketSnapshot.objects.count(), before)
        self.assertEqual(run.details['steps'][0]['step_name'], DemoAutomationRun.ActionType.SIMULATE_TICK)

    def test_execute_generate_signals_creates_signals_and_run(self):
        run = execute_demo_action(action_type=DemoAutomationRun.ActionType.GENERATE_SIGNALS)

        self.assertEqual(run.status, DemoAutomationRun.Status.SUCCESS)
        self.assertGreater(MarketSignal.objects.count(), 0)
        self.assertEqual(run.details['result']['signals_created'] + run.details['result']['signals_updated'], MarketSignal.objects.count())

    def test_execute_revalue_portfolio_creates_snapshot(self):
        before = PaperPortfolioSnapshot.objects.count()

        run = execute_demo_action(action_type=DemoAutomationRun.ActionType.REVALUE_PORTFOLIO)

        self.assertEqual(run.status, DemoAutomationRun.Status.SUCCESS)
        self.assertGreater(PaperPortfolioSnapshot.objects.count(), before)
        self.assertEqual(run.details['result']['account_slug'], 'demo-paper-account')

    def test_execute_generate_trade_reviews_creates_reviews(self):
        run = execute_demo_action(action_type=DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS)

        self.assertEqual(run.status, DemoAutomationRun.Status.SUCCESS)
        self.assertGreater(TradeReview.objects.count(), 0)
        self.assertEqual(run.details['result']['reviews_processed'], TradeReview.objects.count())

    def test_run_demo_cycle_records_ordered_step_results(self):
        run = run_demo_cycle(triggered_from=DemoAutomationRun.TriggeredFrom.AUTOMATION_PAGE)

        self.assertEqual(run.status, DemoAutomationRun.Status.SUCCESS)
        self.assertEqual(run.action_type, DemoAutomationRun.ActionType.RUN_DEMO_CYCLE)
        self.assertEqual(
            [step['step_name'] for step in run.details['steps']],
            [
                DemoAutomationRun.ActionType.SIMULATE_TICK,
                DemoAutomationRun.ActionType.GENERATE_SIGNALS,
                DemoAutomationRun.ActionType.REVALUE_PORTFOLIO,
                DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS,
            ],
        )
        self.assertTrue(all(step['status'] == 'SUCCESS' for step in run.details['steps']))


class DemoAutomationApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('3'), account=get_active_account())
        self.client = APIClient()

    def test_post_action_endpoints_return_run_payloads(self):
        cases = [
            ('automation_demo:simulate-tick', DemoAutomationRun.ActionType.SIMULATE_TICK),
            ('automation_demo:generate-signals', DemoAutomationRun.ActionType.GENERATE_SIGNALS),
            ('automation_demo:revalue-portfolio', DemoAutomationRun.ActionType.REVALUE_PORTFOLIO),
            ('automation_demo:generate-trade-reviews', DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS),
            ('automation_demo:run-demo-cycle', DemoAutomationRun.ActionType.RUN_DEMO_CYCLE),
        ]

        for route_name, action_type in cases:
            response = self.client.post(reverse(route_name), {'triggered_from': 'automation_page'}, format='json')
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload['action_type'], action_type)
            self.assertEqual(payload['triggered_from'], 'automation_page')
            self.assertIn(payload['status'], ['SUCCESS', 'PARTIAL', 'FAILED'])

    def test_runs_and_summary_endpoints_return_recent_history(self):
        execute_demo_action(action_type=DemoAutomationRun.ActionType.SIMULATE_TICK)
        run = execute_demo_action(action_type=DemoAutomationRun.ActionType.SYNC_DEMO_STATE)

        runs_response = self.client.get(reverse('automation_demo:run-list'))
        detail_response = self.client.get(reverse('automation_demo:run-detail', kwargs={'pk': run.pk}))
        summary_response = self.client.get(reverse('automation_demo:summary'))

        self.assertEqual(runs_response.status_code, 200)
        self.assertGreaterEqual(len(runs_response.json()), 2)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()['id'], run.id)
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('latest_run', summary_response.json())
        self.assertIn(DemoAutomationRun.ActionType.SYNC_DEMO_STATE, summary_response.json()['last_by_action'])
