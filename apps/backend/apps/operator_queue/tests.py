from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.operator_queue.models import OperatorDecisionLog, OperatorQueueStatus
from apps.operator_queue.services import ensure_queue_item_for_pending_approval
from apps.paper_trading.models import PaperTrade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.services import generate_trade_proposal
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class OperatorQueueTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='automation')
        self.client = APIClient()

    def _create_pending(self):
        pending = PendingApproval.objects.create(
            proposal=self.proposal,
            market=self.market,
            paper_account=self.account,
            requested_action='BUY',
            suggested_side='YES',
            suggested_quantity=Decimal('1.0000'),
            policy_decision=ApprovalDecisionType.APPROVAL_REQUIRED,
            summary='Approval required for test',
            rationale='Created for operator queue tests',
            metadata={'source': 'semi_auto_demo'},
        )
        return pending

    def test_create_queue_item_from_pending_approval_and_deduplicate(self):
        pending = self._create_pending()
        item = ensure_queue_item_for_pending_approval(pending_approval=pending)
        item2 = ensure_queue_item_for_pending_approval(pending_approval=pending)
        self.assertEqual(item.id, item2.id)

    def test_approve_executes_pending_approval_trade(self):
        pending = self._create_pending()
        item = ensure_queue_item_for_pending_approval(pending_approval=pending)

        response = self.client.post(reverse('operator_queue:approve', kwargs={'pk': item.id}), {'decision_note': 'ship it'}, format='json')
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(pending.status, PendingApprovalStatus.EXECUTED)
        self.assertEqual(item.status, OperatorQueueStatus.EXECUTED)
        self.assertIsNotNone(item.related_trade_id)

    def test_reject_queue_item(self):
        pending = self._create_pending()
        item = ensure_queue_item_for_pending_approval(pending_approval=pending)

        response = self.client.post(reverse('operator_queue:reject', kwargs={'pk': item.id}), {'decision_note': 'nope'}, format='json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(item.status, OperatorQueueStatus.REJECTED)
        self.assertEqual(pending.status, PendingApprovalStatus.REJECTED)

    def test_snooze_queue_item(self):
        pending = self._create_pending()
        item = ensure_queue_item_for_pending_approval(pending_approval=pending)

        response = self.client.post(reverse('operator_queue:snooze', kwargs={'pk': item.id}), {'decision_note': 'later', 'snooze_hours': 2}, format='json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, OperatorQueueStatus.SNOOZED)
        self.assertIsNotNone(item.snoozed_until)

    def test_list_and_summary_endpoints(self):
        pending = self._create_pending()
        item = ensure_queue_item_for_pending_approval(pending_approval=pending)

        list_response = self.client.get(reverse('operator_queue:list'))
        summary_response = self.client.get(reverse('operator_queue:summary'))
        detail_response = self.client.get(reverse('operator_queue:detail', kwargs={'pk': item.id}))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn('pending_count', summary_response.json())

    def test_rebuild_creates_items_from_existing_pending(self):
        self._create_pending()
        response = self.client.post(reverse('operator_queue:rebuild'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()['created'], 1)
        self.assertTrue(OperatorDecisionLog.objects.count() == 0)
        self.assertEqual(PaperTrade.objects.count(), 0)
