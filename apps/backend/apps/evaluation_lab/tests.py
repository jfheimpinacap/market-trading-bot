from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.continuous_demo.models import ContinuousDemoSession, SessionStatus
from apps.evaluation_lab.services import build_run_for_continuous_session
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.models import PaperPortfolioSnapshot
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome, TradeReviewStatus
from apps.safety_guard.models import SafetyEvent, SafetyEventType, SafetySeverity, SafetyEventSource


class EvaluationLabTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.order_by('id').first()
        self.client = APIClient()

    def _build_session_with_data(self):
        session = ContinuousDemoSession.objects.create(session_status=SessionStatus.STOPPED)
        session.started_at = session.created_at
        session.finished_at = session.created_at
        session.save(update_fields=['started_at', 'finished_at'])

        trade = execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('1.0000'),
            account=self.account,
        )
        TradeReview.objects.create(
            paper_trade=trade,
            paper_account=self.account,
            market=self.market,
            review_status=TradeReviewStatus.REVIEWED,
            outcome=TradeReviewOutcome.FAVORABLE,
            score=Decimal('70.00'),
            confidence=Decimal('0.70'),
            summary='Good trade',
        )
        PaperPortfolioSnapshot.objects.create(
            account=self.account,
            cash_balance=self.account.cash_balance,
            equity=Decimal('10010.00'),
            realized_pnl=Decimal('10.00'),
            unrealized_pnl=Decimal('0.00'),
            total_pnl=Decimal('10.00'),
            open_positions_count=1,
        )
        SafetyEvent.objects.create(
            event_type=SafetyEventType.WARNING,
            severity=SafetySeverity.WARNING,
            source=SafetyEventSource.CONTINUOUS_DEMO,
            message='Test warning',
        )
        return session

    def test_build_metrics_for_session(self):
        session = self._build_session_with_data()
        run = build_run_for_continuous_session(session)

        self.assertEqual(run.status, 'READY')
        self.assertIsNotNone(run.metric_set)
        self.assertGreaterEqual(run.metric_set.trades_executed_count, 1)
        self.assertEqual(run.metric_set.favorable_reviews_count, 1)

    def test_summary_endpoint(self):
        session = self._build_session_with_data()
        build_run_for_continuous_session(session)

        response = self.client.get(reverse('evaluation_lab:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['completed_runs'], 1)
        self.assertIsNotNone(payload['latest_run'])

    def test_run_detail_endpoint(self):
        session = self._build_session_with_data()
        run = build_run_for_continuous_session(session)

        response = self.client.get(reverse('evaluation_lab:run-detail', kwargs={'pk': run.id}))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['id'], run.id)
        self.assertEqual(payload['metric_set']['favorable_reviews_count'], 1)
