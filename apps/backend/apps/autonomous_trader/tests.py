from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.autonomous_trader.models import (
    AutonomousLearningHandoff,
    AutonomousOutcomeHandoffRecommendation,
    AutonomousPostmortemHandoff,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)
from apps.autonomous_trader.services.candidate_intake import consolidate_candidates
from apps.autonomous_trader.services.decisioning import decide_candidate
from apps.autonomous_trader.services.execution import execute_candidate
from apps.markets.models import Event, Market, MarketStatus, Provider
from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun, OpportunityFusionCandidate
from apps.paper_trading.models import PaperTrade, PaperTradeStatus, PaperTradeType
from apps.paper_trading.services.portfolio import ensure_demo_account


class AutonomousTraderFlowTests(TestCase):
    def setUp(self):
        ensure_demo_account()
        self.client = APIClient()
        provider = Provider.objects.create(name='Demo Provider', slug='demo-provider')
        event = Event.objects.create(provider=provider, title='Election', slug='election-2026')
        self.market = Market.objects.create(
            provider=provider,
            event=event,
            title='Will candidate X win?',
            slug='candidate-x-win',
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('0.40'),
            current_no_price=Decimal('0.60'),
            volume_total=Decimal('100000.00'),
            liquidity=Decimal('50000.00'),
            close_time=timezone.now() + timezone.timedelta(days=20),
        )
        runtime_run = OpportunityCycleRuntimeRun.objects.create(started_at=timezone.now())
        OpportunityFusionCandidate.objects.create(
            runtime_run=runtime_run,
            linked_market=self.market,
            adjusted_edge=Decimal('0.1200'),
            confidence_score=Decimal('0.8000'),
            market_probability=Decimal('0.4000'),
            metadata={},
        )

    def _create_closed_loss_outcome(self, *, watch_status='EXIT_REVIEW_REQUIRED', with_trade=True):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        decision = decide_candidate(candidate=intake.candidates[0])
        execution = execute_candidate(decision=decision)
        if with_trade:
            account, _ = ensure_demo_account()
            trade = PaperTrade.objects.create(
                account=account,
                market=self.market,
                side='YES',
                trade_type=PaperTradeType.BUY,
                quantity=Decimal('5'),
                price=Decimal('0.60'),
                gross_amount=Decimal('3.00'),
                fees=Decimal('0.01'),
                status=PaperTradeStatus.EXECUTED,
                executed_at=timezone.now(),
                metadata={'risk_assessment_id': None},
            )
            execution.linked_paper_trade = trade
            execution.execution_status = 'FILLED'
            execution.save(update_fields=['linked_paper_trade', 'execution_status', 'updated_at'])

        watch = AutonomousTradeWatchRecord.objects.create(
            linked_execution=execution,
            watch_status=watch_status,
            sentiment_shift_detected=True,
            risk_change_detected=True,
        )
        return AutonomousTradeOutcome.objects.create(
            linked_execution=execution,
            linked_watch_record=watch,
            outcome_type='LOSS_EXIT',
            outcome_status='CLOSED',
            outcome_summary='Closed with loss for test.',
            send_to_postmortem=True,
            send_to_learning=True,
            metadata={'paper_only': True},
        )

    def test_candidate_intake_and_decision(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        self.assertGreaterEqual(len(intake.candidates), 1)
        decision = decide_candidate(candidate=intake.candidates[0])
        self.assertTrue(decision.decision_type)

    def test_loss_exit_closed_generates_postmortem_handoff(self):
        self._create_closed_loss_outcome()

        response = self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AutonomousPostmortemHandoff.objects.exists())

    def test_duplicate_handoff_is_skipped(self):
        self._create_closed_loss_outcome()
        self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')
        self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')

        self.assertTrue(AutonomousPostmortemHandoff.objects.filter(handoff_status='DUPLICATE_SKIPPED').exists())

    def test_open_outcome_is_not_emitted(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        decision = decide_candidate(candidate=intake.candidates[0])
        execution = execute_candidate(decision=decision)
        AutonomousTradeOutcome.objects.create(
            linked_execution=execution,
            outcome_type='NO_ACTION',
            outcome_status='OPEN',
            outcome_summary='Still open',
        )

        self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')
        self.assertFalse(AutonomousPostmortemHandoff.objects.exists())
        self.assertTrue(
            AutonomousOutcomeHandoffRecommendation.objects.filter(recommendation_type='WAIT_FOR_OUTCOME_CLOSURE').exists()
        )

    def test_learning_handoff_created_when_corresponds(self):
        self._create_closed_loss_outcome()
        self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')
        self.assertTrue(AutonomousLearningHandoff.objects.exists())

    def test_outcome_handoff_summary_endpoint(self):
        self._create_closed_loss_outcome(with_trade=False)
        self.client.post('/api/autonomous-trader/run-outcome-handoff/', {'actor': 'test-suite'}, format='json')

        response = self.client.get('/api/autonomous-trader/outcome-handoff-summary/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('considered_outcome_count', payload)
        self.assertIn('duplicate_skipped_count', payload)
