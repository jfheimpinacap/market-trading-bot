from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EvaluationRun, EvaluationRunStatus, EvaluationScope, EvaluationMarketScope, EvaluationMetricSet
from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningMemoryEntry, LearningOutcome, LearningRebuildRun
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

    def test_rebuild_endpoint_creates_rebuild_run_trace(self):
        self._seed_unfavorable_review()
        response = self.client.post(reverse('learning_memory:rebuild'), {'triggered_from': 'manual'}, format='json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['triggered_from'], 'manual')
        self.assertIn(payload['status'], ['SUCCESS', 'PARTIAL', 'FAILED'])
        self.assertTrue(LearningRebuildRun.objects.filter(id=payload['id']).exists())

        list_response = self.client.get(reverse('learning_memory:rebuild-run-list'))
        detail_response = self.client.get(reverse('learning_memory:rebuild-run-detail', kwargs={'pk': payload['id']}))
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(len(list_response.json()), 1)
        self.assertEqual(detail_response.status_code, 200)


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


class PostmortemLearningLoopTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def _create_postmortem_run(self):
        trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('3.0000'), account=self.account).trade
        self.market.current_yes_price = Decimal('44.0000')
        self.market.current_market_probability = Decimal('0.4400')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])
        review = generate_trade_review(trade, refresh_existing=True).review
        from apps.postmortem_agents.services.board import run_postmortem_board

        result = run_postmortem_board(related_trade_review_id=review.id, force_learning_rebuild=False)
        return result.board_run

    def test_pattern_derivation_and_summary_endpoint(self):
        self._create_postmortem_run()
        response = self.client.post(reverse('learning_memory:run-postmortem-loop'), {}, format='json')
        self.assertEqual(response.status_code, 200)

        patterns = self.client.get(reverse('learning_memory:failure-patterns'))
        self.assertEqual(patterns.status_code, 200)
        self.assertGreaterEqual(len(patterns.json()), 1)

        summary = self.client.get(reverse('learning_memory:postmortem-loop-summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('runs_processed', summary.json())

    def test_adjustment_status_activation_and_expire(self):
        self._create_postmortem_run()
        self.client.post(reverse('learning_memory:run-postmortem-loop'), {}, format='json')
        adjustments = self.client.get(reverse('learning_memory:adjustments')).json()
        self.assertGreaterEqual(len(adjustments), 1)
        adjustment_id = adjustments[0]['id']

        activate = self.client.post(reverse('learning_memory:activate-adjustment', kwargs={'pk': adjustment_id}), {}, format='json')
        self.assertEqual(activate.status_code, 200)
        self.assertEqual(activate.json()['status'], 'ACTIVE')

        expire = self.client.post(reverse('learning_memory:expire-adjustment', kwargs={'pk': adjustment_id}), {}, format='json')
        self.assertEqual(expire.status_code, 200)
        self.assertEqual(expire.json()['status'], 'EXPIRED')

    def test_application_records_and_manual_review_recommendation(self):
        for _ in range(6):
            self._create_postmortem_run()
        self.client.post(reverse('learning_memory:run-postmortem-loop'), {}, format='json')

        applications = self.client.get(reverse('learning_memory:application-records'))
        self.assertEqual(applications.status_code, 200)
        self.assertGreaterEqual(len(applications.json()), 1)

        recommendations = self.client.get(reverse('learning_memory:recommendations'))
        self.assertEqual(recommendations.status_code, 200)
        types = {item['recommendation_type'] for item in recommendations.json()}
        self.assertIn('REQUIRE_MANUAL_LEARNING_REVIEW', types)
