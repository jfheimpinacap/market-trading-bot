from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EvaluationRun, EvaluationRunStatus, EvaluationScope, EvaluationMarketScope, EvaluationMetricSet
from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningMemoryEntry, LearningOutcome
from apps.learning_memory.services import ingest_recent_reviews, rebuild_active_adjustments
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.postmortem_demo.services import generate_trade_review
from apps.proposal_engine.services import generate_trade_proposal
from apps.risk_demo.services.assessment import assess_trade


class LearningMemoryIngestTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def _seed_unfavorable_review(self):
        trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5.0000'), account=self.account).trade
        self.market.current_yes_price = Decimal('45.0000')
        self.market.current_market_probability = Decimal('0.4500')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])
        return generate_trade_review(trade, refresh_existing=True).review

    def test_ingest_recent_reviews_creates_memory_entries(self):
        review = self._seed_unfavorable_review()

        created = ingest_recent_reviews()

        self.assertEqual(created, 1)
        entry = LearningMemoryEntry.objects.get(related_review=review)
        self.assertEqual(entry.outcome, LearningOutcome.NEGATIVE)
        self.assertEqual(entry.memory_type, 'trade_pattern')

    def test_rebuild_command_and_summary_endpoint(self):
        self._seed_unfavorable_review()
        run = EvaluationRun.objects.create(
            status=EvaluationRunStatus.READY,
            evaluation_scope=EvaluationScope.SESSION,
            market_scope=EvaluationMarketScope.MIXED,
        )
        EvaluationMetricSet.objects.create(
            run=run,
            blocked_count=4,
            safety_events_count=2,
            unfavorable_review_streak=3,
            favorable_review_rate=Decimal('0.1000'),
            total_pnl=Decimal('-100.00'),
        )

        call_command('rebuild_learning_memory')

        response = self.client.get(reverse('learning_memory:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload['total_memory_entries'], 1)
        self.assertIn('negative_patterns_detected', payload)


class LearningInfluenceIntegrationTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_proposal_and_risk_receive_learning_influence(self):
        LearningAdjustment.objects.create(
            adjustment_type=LearningAdjustmentType.CONFIDENCE_BIAS,
            scope_type='global',
            scope_key='global',
            is_active=True,
            magnitude=Decimal('-0.0900'),
            reason='Test conservative confidence bias.',
        )
        LearningAdjustment.objects.create(
            adjustment_type=LearningAdjustmentType.QUANTITY_BIAS,
            scope_type='source_type',
            scope_key=self.market.source_type,
            is_active=True,
            magnitude=Decimal('-0.2000'),
            reason='Test conservative quantity bias.',
        )
        LearningAdjustment.objects.create(
            adjustment_type=LearningAdjustmentType.RISK_CAUTION_BIAS,
            scope_type='provider',
            scope_key=self.market.provider.slug,
            is_active=True,
            magnitude=Decimal('-0.1200'),
            reason='Test conservative caution bias.',
        )

        proposal = generate_trade_proposal(market=self.market, paper_account=self.account)
        assessment = assess_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('2.0000'))

        self.assertIn('Learning memory influence', proposal.rationale)
        self.assertTrue(any(item['code'] == 'LEARNING_MEMORY_CAUTION' for item in assessment.warnings))

    def test_adjustments_rebuild_creates_global_bias_after_negative_memory(self):
        for i in range(5):
            LearningMemoryEntry.objects.create(
                memory_type='trade_pattern',
                source_type='demo',
                provider=self.market.provider,
                market=self.market,
                outcome='negative',
                score_delta=Decimal('-10.00'),
                confidence_delta=Decimal('-0.0500'),
                quantity_bias_delta=Decimal('-0.1000'),
                summary=f'Negative memory {i}',
                rationale='Synthetic negative pattern.',
            )

        rebuild_active_adjustments()

        global_bias = LearningAdjustment.objects.get(
            adjustment_type=LearningAdjustmentType.CONFIDENCE_BIAS,
            scope_type='global',
            scope_key='global',
        )
        self.assertTrue(global_bias.is_active)
        self.assertLess(global_bias.magnitude, Decimal('0.0000'))
