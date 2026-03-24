from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Event, Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.risk_demo.models import TradeRiskAssessment, TradeRiskDecision
from apps.risk_demo.services.assessment import assess_trade
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class RiskAssessmentServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_insufficient_cash_blocks_trade(self):
        self.account.cash_balance = Decimal('5.00')
        self.account.save(update_fields=['cash_balance'])

        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10.0000'),
        )

        self.assertEqual(assessment.decision, TradeRiskDecision.BLOCK)
        self.assertFalse(assessment.is_actionable)
        self.assertTrue(any(item['code'] == 'INSUFFICIENT_CASH' for item in assessment.warnings))

    def test_terminal_market_blocks_trade(self):
        terminal_market = Market.objects.get(slug='will-export-controls-tighten-before-november-2025')
        terminal_market.status = MarketStatus.RESOLVED
        terminal_market.save(update_fields=['status'])

        assessment = assess_trade(
            market=terminal_market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        self.assertEqual(assessment.decision, TradeRiskDecision.BLOCK)
        self.assertIn('not tradable', assessment.summary.lower())

    def test_reasonable_trade_is_approved_or_cautioned(self):
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        self.assertIn(assessment.decision, {TradeRiskDecision.APPROVE, TradeRiskDecision.CAUTION})
        self.assertGreaterEqual(assessment.score, Decimal('0.00'))
        self.assertLessEqual(assessment.score, Decimal('100.00'))

    def test_large_trade_is_cautioned_or_blocked(self):
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('120.0000'),
        )

        self.assertIn(assessment.decision, {TradeRiskDecision.CAUTION, TradeRiskDecision.BLOCK})
        self.assertTrue(any(item['code'] in {'LARGE_TRADE', 'VERY_LARGE_TRADE'} for item in assessment.warnings))

    def test_existing_market_concentration_creates_warning(self):
        execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('80.0000'),
            account=self.account,
        )

        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10.0000'),
        )

        self.assertIn(assessment.decision, {TradeRiskDecision.CAUTION, TradeRiskDecision.BLOCK})
        self.assertTrue(any(item['code'] == 'MARKET_CONCENTRATION' for item in assessment.warnings))


    def test_risk_assessment_works_for_real_read_only_market(self):
        provider = Provider.objects.create(name='Kalshi Risk Real', slug='kalshi-risk-real')
        event = Event.objects.create(provider=provider, title='Risk Real Event', slug='risk-real-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')
        market = Market.objects.create(
            provider=provider,
            event=event,
            title='Risk Real Market',
            slug='risk-real-market',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_yes_price=Decimal('57.0000'),
            current_no_price=Decimal('43.0000'),
            current_market_probability=Decimal('0.5700'),
        )

        assessment = assess_trade(
            market=market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        self.assertIn(assessment.decision, {TradeRiskDecision.APPROVE, TradeRiskDecision.CAUTION})
        self.assertEqual(assessment.market.source_type, MarketSourceType.REAL_READ_ONLY)


class RiskAssessmentApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_post_assess_trade_endpoint_returns_persisted_assessment(self):
        response = self.client.post(
            reverse('risk_demo:assess-trade'),
            {
                'market_id': self.market.id,
                'trade_type': 'BUY',
                'side': 'YES',
                'quantity': '10.0000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()['assessment']
        self.assertEqual(payload['market'], self.market.id)
        self.assertIn(payload['decision'], ['APPROVE', 'CAUTION', 'BLOCK'])
        self.assertEqual(TradeRiskAssessment.objects.count(), 1)

    def test_assessments_list_endpoint_returns_recent_rows(self):
        assess_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('1.0000'))
        assess_trade(market=self.market, trade_type='BUY', side='NO', quantity=Decimal('2.0000'))

        response = self.client.get(reverse('risk_demo:assessment-list'), {'market': self.market.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertTrue(all(item['market'] == self.market.id for item in response.json()))
