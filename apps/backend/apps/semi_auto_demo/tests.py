from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.models import PaperTrade
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus
from apps.semi_auto_demo.services import run_evaluate_only, run_scan_and_execute
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class SemiAutoDemoServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_evaluate_only_generates_classification_without_executions(self):
        run = run_evaluate_only()

        self.assertGreater(run.markets_evaluated, 0)
        self.assertEqual(run.auto_executed_count, 0)
        self.assertEqual(PaperTrade.objects.count(), 0)
        self.assertTrue(len(run.details['results']) > 0)

    def test_auto_approve_path_executes_paper_trade_when_safe(self):
        run = run_scan_and_execute()

        self.assertGreaterEqual(run.auto_executed_count, 1)
        self.assertGreaterEqual(PaperTrade.objects.count(), 1)

    def test_approval_required_creates_pending_approval(self):
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('70.0000'), account=self.account)

        run = run_scan_and_execute()

        self.assertGreaterEqual(run.approval_required_count, 1)
        self.assertTrue(PendingApproval.objects.filter(status=PendingApprovalStatus.PENDING).exists())

    def test_hard_block_never_executes(self):
        self.account.cash_balance = Decimal('0.10')
        self.account.save(update_fields=['cash_balance'])

        run = run_scan_and_execute()

        self.assertGreater(run.blocked_count, 0)


class SemiAutoDemoApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        ensure_demo_account()
        self.client = APIClient()

    def test_main_endpoints_are_operational(self):
        evaluate_response = self.client.post(reverse('semi_auto_demo:evaluate'), {}, format='json')
        self.assertEqual(evaluate_response.status_code, 200)

        run_response = self.client.post(reverse('semi_auto_demo:run'), {}, format='json')
        self.assertEqual(run_response.status_code, 200)
        run_id = run_response.json()['id']

        runs_response = self.client.get(reverse('semi_auto_demo:run-list'))
        detail_response = self.client.get(reverse('semi_auto_demo:run-detail', kwargs={'pk': run_id}))
        pending_response = self.client.get(reverse('semi_auto_demo:pending-approval-list'))
        summary_response = self.client.get(reverse('semi_auto_demo:summary'))

        self.assertEqual(runs_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)

    def test_approve_pending_approval_executes_trade(self):
        account = get_active_account()
        market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        run_scan_and_execute()

        pending = PendingApproval.objects.create(
            proposal=market.trade_proposals.order_by('-created_at').first(),
            market=market,
            paper_account=account,
            requested_action='BUY',
            suggested_side='YES',
            suggested_quantity=Decimal('1.0000'),
            policy_decision=ApprovalDecisionType.APPROVAL_REQUIRED,
            summary='Manual approval required',
            rationale='Test pending approval flow.',
        )

        response = self.client.post(reverse('semi_auto_demo:pending-approval-approve', kwargs={'pk': pending.id}), {'decision_note': 'approved'}, format='json')
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingApprovalStatus.EXECUTED)
        self.assertIsNotNone(pending.executed_trade_id)

    def test_reject_pending_approval_marks_as_rejected_without_trade(self):
        account = get_active_account()
        market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        run_scan_and_execute()

        pending = PendingApproval.objects.create(
            proposal=market.trade_proposals.order_by('-created_at').first(),
            market=market,
            paper_account=account,
            requested_action='BUY',
            suggested_side='YES',
            suggested_quantity=Decimal('1.0000'),
            policy_decision=ApprovalDecisionType.APPROVAL_REQUIRED,
            summary='Manual approval required',
            rationale='Reject flow test.',
        )

        before_trades = PaperTrade.objects.count()
        response = self.client.post(reverse('semi_auto_demo:pending-approval-reject', kwargs={'pk': pending.id}), {'decision_note': 'reject'}, format='json')
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, PendingApprovalStatus.REJECTED)
        self.assertEqual(PaperTrade.objects.count(), before_trades)
