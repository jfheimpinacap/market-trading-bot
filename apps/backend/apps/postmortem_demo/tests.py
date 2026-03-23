from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market, MarketStatus
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome, TradeReviewStatus
from apps.postmortem_demo.services import generate_trade_review, generate_trade_reviews
from apps.risk_demo.models import TradeRiskAssessment
from apps.signals.models import MarketSignal, MarketSignalStatus, MockAgent, SignalDirection


class TradeReviewGenerationTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.agent = MockAgent.objects.create(
            name='Postmortem Signal Agent',
            slug='postmortem-signal-agent',
            role_type='POSTMORTEM',
            description='Test-only signal agent.',
        )

    def _create_signal(self, *, actionable: bool, direction: str):
        return MarketSignal.objects.create(
            market=self.market,
            agent=self.agent,
            signal_type='OPPORTUNITY',
            status=MarketSignalStatus.ACTIVE,
            direction=direction,
            score=Decimal('72.00'),
            confidence=Decimal('0.66'),
            headline='Test market signal',
            thesis='Synthetic signal for trade review tests.',
            rationale='Used to verify post-mortem context capture.',
            signal_probability=Decimal('0.5800'),
            market_probability_at_signal=Decimal('0.5400'),
            edge_estimate=Decimal('0.0400'),
            is_actionable=actionable,
        )

    def _create_risk_assessment(self, *, decision: str, quantity: Decimal):
        return TradeRiskAssessment.objects.create(
            market=self.market,
            paper_account=self.account,
            side='YES',
            trade_type='BUY',
            quantity=quantity,
            requested_price=self.market.current_yes_price,
            current_market_probability=self.market.current_market_probability,
            current_yes_price=self.market.current_yes_price,
            current_no_price=self.market.current_no_price,
            decision=decision,
            score=Decimal('61.00'),
            confidence=Decimal('0.74'),
            summary='Synthetic risk verdict',
            rationale='Used to verify post-mortem risk context.',
            warnings=[],
            is_actionable=decision != 'BLOCK',
        )

    def test_generate_review_favorable(self):
        self._create_signal(actionable=True, direction=SignalDirection.BULLISH)
        trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('10'), account=self.account).trade
        self.market.current_yes_price = Decimal('61.0000')
        self.market.current_market_probability = Decimal('0.6100')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])

        result = generate_trade_review(trade, refresh_existing=True)

        self.assertTrue(result.created)
        self.assertEqual(result.review.outcome, TradeReviewOutcome.FAVORABLE)
        self.assertEqual(result.review.review_status, TradeReviewStatus.REVIEWED)
        self.assertEqual(result.review.price_delta, Decimal('7.0000'))
        self.assertGreater(result.review.score, Decimal('50.00'))
        self.assertIn('moved in the intended direction', result.review.summary)

    def test_generate_review_unfavorable(self):
        self._create_signal(actionable=False, direction=SignalDirection.BEARISH)
        risk = self._create_risk_assessment(decision='BLOCK', quantity=Decimal('10'))
        trade = execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10'),
            account=self.account,
            metadata={'risk_assessment_id': risk.id, 'risk_decision': risk.decision},
        ).trade
        self.market.current_yes_price = Decimal('48.0000')
        self.market.current_market_probability = Decimal('0.4800')
        self.market.status = MarketStatus.PAUSED
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'status', 'updated_at'])

        review = generate_trade_review(trade, refresh_existing=True).review

        self.assertEqual(review.outcome, TradeReviewOutcome.UNFAVORABLE)
        self.assertEqual(review.risk_decision_at_trade, 'BLOCK')
        self.assertIn('monitor-only', review.rationale)
        self.assertIn('bypassed the demo risk guard', review.recommendation)
        self.assertLess(review.score, Decimal('50.00'))

    def test_generate_review_neutral(self):
        self._create_signal(actionable=True, direction=SignalDirection.BULLISH)
        trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('10'), account=self.account).trade
        self.market.current_yes_price = Decimal('55.0000')
        self.market.current_market_probability = Decimal('0.5500')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])

        review = generate_trade_review(trade, refresh_existing=True).review

        self.assertEqual(review.outcome, TradeReviewOutcome.NEUTRAL)
        self.assertEqual(review.price_delta, Decimal('1.0000'))
        self.assertIn('barely moved', review.summary)

    def test_generate_trade_reviews_command_outputs_summary(self):
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5'), account=self.account)
        stdout = StringIO()

        call_command('generate_trade_reviews', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Generating demo trade reviews using local post-mortem heuristics...', output)
        self.assertIn('Trade review generation complete.', output)
        self.assertEqual(TradeReview.objects.count(), 1)


class TradeReviewApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.account = get_active_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.other_market = Market.objects.get(slug='will-voter-turnout-exceed-64-in-the-2028-election')

        first_trade = execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5'), account=self.account).trade
        self.market.current_yes_price = Decimal('60.0000')
        self.market.current_market_probability = Decimal('0.6000')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])
        self.first_review = generate_trade_review(first_trade, refresh_existing=True).review

        second_trade = execute_paper_trade(market=self.other_market, trade_type='BUY', side='YES', quantity=Decimal('5'), account=self.account).trade
        self.other_market.current_yes_price = Decimal('36.0000')
        self.other_market.current_market_probability = Decimal('0.3600')
        self.other_market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])
        self.second_review = generate_trade_review(second_trade, refresh_existing=True).review

    def test_review_list_endpoint_returns_rows(self):
        response = self.client.get(reverse('postmortem_demo:review-list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertIn('market_title', payload[0])
        self.assertIn('trade_executed_at', payload[0])

    def test_review_list_filters_by_market_outcome_and_account(self):
        response = self.client.get(
            reverse('postmortem_demo:review-list'),
            {
                'market': self.market.id,
                'account': self.account.id,
                'outcome': 'FAVORABLE',
                'ordering': '-score',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['market'], self.market.id)
        self.assertEqual(payload[0]['outcome'], 'FAVORABLE')

    def test_review_detail_and_summary_endpoints_work(self):
        detail_response = self.client.get(reverse('postmortem_demo:review-detail', kwargs={'pk': self.first_review.pk}))
        summary_response = self.client.get(reverse('postmortem_demo:review-summary'))

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()['id'], self.first_review.id)
        self.assertIn('rationale', detail_response.json())
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()['total_reviews'], 2)
        self.assertEqual(summary_response.json()['favorable_reviews'], 1)
        self.assertEqual(summary_response.json()['unfavorable_reviews'], 1)

    def test_generate_trade_reviews_marks_existing_reviews_stale_without_refresh(self):
        self.market.current_yes_price = Decimal('63.0000')
        self.market.current_market_probability = Decimal('0.6300')
        self.market.save(update_fields=['current_yes_price', 'current_market_probability', 'updated_at'])

        results = generate_trade_reviews(trade_id=self.first_review.paper_trade_id, refresh_existing=False)

        self.first_review.refresh_from_db()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].created)
        self.assertTrue(results[0].stale_marked)
        self.assertEqual(self.first_review.review_status, TradeReviewStatus.STALE)
