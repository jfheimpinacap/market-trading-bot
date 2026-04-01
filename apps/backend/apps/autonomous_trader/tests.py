from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.autonomous_trader.models import (
    AutonomousFeedbackCandidateContext,
    AutonomousFeedbackInfluenceRecord,
    AutonomousFeedbackReuseRun,
    AutonomousFeedbackRecommendation,
    AutonomousLearningHandoff,
    AutonomousSizingContext,
    AutonomousSizingDecision,
    AutonomousSizingRecommendation,
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
from apps.autonomous_trader.services.kelly_sizing import run_sizing_bridge
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

    def test_sizing_context_created_for_eligible_candidate(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        run_sizing_bridge(cycle_run_id=cycle.id, limit=10)
        self.assertTrue(AutonomousSizingContext.objects.filter(linked_candidate=intake.candidates[0]).exists())

    def test_kelly_and_adjustments_are_conservative(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        run_sizing_bridge(cycle_run_id=cycle.id, limit=10)
        decision = AutonomousSizingDecision.objects.filter(linked_candidate=intake.candidates[0]).latest('id')
        self.assertLessEqual(Decimal(decision.applied_fraction), Decimal('0.050000'))
        self.assertLessEqual(Decimal(decision.notional_after_adjustment or 0), Decimal('1000.00'))

    def test_feedback_caution_reduces_size(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        candidate = intake.candidates[0]
        candidate.system_probability = Decimal('0.6200')
        candidate.market_probability = Decimal('0.5500')
        candidate.save(update_fields=['system_probability', 'market_probability', 'updated_at'])
        reuse_run = AutonomousFeedbackReuseRun.objects.create()
        context = AutonomousFeedbackCandidateContext.objects.create(
            linked_reuse_run=reuse_run,
            linked_cycle_run=cycle,
            linked_candidate=candidate,
            linked_market=self.market,
            retrieval_status='HITS_FOUND',
        )
        AutonomousFeedbackInfluenceRecord.objects.create(
            linked_candidate_context=context,
            linked_candidate=candidate,
            influence_type='CAUTION_BOOST',
            influence_status='APPLIED',
            influence_reason_codes=['REPEAT_LOSS_PATTERN'],
        )
        run_sizing_bridge(cycle_run_id=cycle.id, limit=10)
        decision = AutonomousSizingDecision.objects.filter(linked_candidate=candidate).latest('id')
        self.assertIn('FEEDBACK_CAUTION_DISCOUNT', decision.adjustment_reason_codes)

    def test_sizing_summary_endpoint(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        consolidate_candidates(cycle_run=cycle)
        self.client.post('/api/autonomous-trader/run-sizing/', {'cycle_run_id': cycle.id}, format='json')
        response = self.client.get('/api/autonomous-trader/sizing-summary/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('considered_candidate_count', payload)
        self.assertIn('sized_for_execution_count', payload)


class AutonomousFeedbackReuseTests(TestCase):
    def setUp(self):
        ensure_demo_account()
        self.client = APIClient()
        provider = Provider.objects.create(name='Demo Provider', slug='demo-provider-feedback')
        event = Event.objects.create(provider=provider, title='Macro', slug='macro-2026')
        self.market = Market.objects.create(
            provider=provider,
            event=event,
            title='Will inflation cool by Q4?',
            slug='inflation-cool-q4',
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('0.55'),
            current_no_price=Decimal('0.45'),
            volume_total=Decimal('500000.00'),
            liquidity=Decimal('250000.00'),
            close_time=timezone.now() + timezone.timedelta(days=45),
        )
        runtime_run = OpportunityCycleRuntimeRun.objects.create(started_at=timezone.now())
        OpportunityFusionCandidate.objects.create(
            runtime_run=runtime_run,
            linked_market=self.market,
            adjusted_edge=Decimal('0.0900'),
            confidence_score=Decimal('0.7900'),
            market_probability=Decimal('0.5500'),
            metadata={},
        )
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        self.candidate = intake.candidates[0]

    @patch('apps.autonomous_trader.services.feedback_reuse.feedback_retrieval.run_assist')
    def test_feedback_retrieval_context_created(self, mock_run_assist):
        mock_run_assist.return_value = type(
            'Assist',
            (),
            {
                'summary': {'matches': 1, 'prior_failure_modes': ['late sentiment reversal'], 'top_lessons': ['tighten exits']},
                'retrieval_run': type('Run', (), {'id': 7})(),
                'precedent_confidence': 0.74,
                'influence_mode': 'confidence_adjust',
                'caution_flags': ['sentiment drift'],
            },
        )()

        response = self.client.post('/api/autonomous-trader/run-feedback-reuse/', {'limit': 5}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AutonomousFeedbackCandidateContext.objects.filter(linked_candidate=self.candidate).exists())

    @patch('apps.autonomous_trader.services.feedback_reuse.feedback_retrieval.run_assist')
    def test_negative_precedent_reduces_confidence(self, mock_run_assist):
        mock_run_assist.return_value = type(
            'Assist',
            (),
            {
                'summary': {'matches': 2, 'prior_failure_modes': ['drawdown'], 'top_lessons': ['reduce confidence']},
                'retrieval_run': type('Run', (), {'id': 8})(),
                'precedent_confidence': 0.81,
                'influence_mode': 'confidence_adjust',
                'caution_flags': ['drawdown'],
            },
        )()
        before = self.candidate.confidence
        self.client.post('/api/autonomous-trader/run-feedback-reuse/', {'limit': 5}, format='json')
        self.candidate.refresh_from_db()
        influence = AutonomousFeedbackInfluenceRecord.objects.filter(linked_candidate=self.candidate).latest('id')
        self.assertEqual(influence.influence_type, 'CONFIDENCE_REDUCTION')
        self.assertLess(self.candidate.confidence, before)

    @patch('apps.autonomous_trader.services.feedback_reuse.feedback_retrieval.run_assist')
    def test_repeat_loss_pattern_blocks_candidate(self, mock_run_assist):
        mock_run_assist.return_value = type(
            'Assist',
            (),
            {
                'summary': {'matches': 3, 'prior_failure_modes': ['repeat loss pattern'], 'top_lessons': ['block recurrence']},
                'retrieval_run': type('Run', (), {'id': 9})(),
                'precedent_confidence': 0.9,
                'influence_mode': 'caution_boost',
                'caution_flags': ['repeat loss'],
            },
        )()
        self.client.post('/api/autonomous-trader/run-feedback-reuse/', {'limit': 5}, format='json')
        self.candidate.refresh_from_db()
        influence = AutonomousFeedbackInfluenceRecord.objects.filter(linked_candidate=self.candidate).latest('id')
        self.assertEqual(influence.influence_type, 'BLOCK_REPEAT_PATTERN')
        self.assertEqual(self.candidate.candidate_status, 'BLOCKED')

    @patch('apps.autonomous_trader.services.feedback_reuse.feedback_retrieval.run_assist')
    def test_no_hits_creates_no_relevant_learning_recommendation(self, mock_run_assist):
        mock_run_assist.return_value = type(
            'Assist',
            (),
            {
                'summary': {'matches': 0, 'prior_failure_modes': [], 'top_lessons': []},
                'retrieval_run': type('Run', (), {'id': 10})(),
                'precedent_confidence': 0.3,
                'influence_mode': 'rationale_only',
                'caution_flags': [],
            },
        )()
        self.client.post('/api/autonomous-trader/run-feedback-reuse/', {'limit': 5}, format='json')
        self.assertTrue(
            AutonomousFeedbackRecommendation.objects.filter(recommendation_type='NO_RELEVANT_LEARNING_FOUND').exists()
        )

    def test_feedback_summary_endpoint(self):
        response = self.client.get('/api/autonomous-trader/feedback-summary/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('considered_candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
