from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Event, Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.policy_engine.models import ApprovalDecision, ApprovalDecisionType
from apps.policy_engine.services import evaluate_trade_policy
from apps.risk_demo.models import TradeRiskDecision
from apps.risk_demo.services.assessment import assess_trade
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class PolicyEvaluationServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_reasonable_small_trade_is_auto_approved(self):
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )
        self.assertEqual(assessment.decision, TradeRiskDecision.APPROVE)

        decision = evaluate_trade_policy(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
            risk_assessment=assessment,
        )

        self.assertEqual(decision.decision, ApprovalDecisionType.AUTO_APPROVE)

    def test_risk_caution_requires_manual_approval(self):
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('70.0000'),
        )
        self.assertEqual(assessment.decision, TradeRiskDecision.CAUTION)

        decision = evaluate_trade_policy(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('70.0000'),
            risk_assessment=assessment,
        )

        self.assertEqual(decision.decision, ApprovalDecisionType.APPROVAL_REQUIRED)

    def test_risk_block_becomes_hard_block(self):
        self.account.cash_balance = Decimal('5.00')
        self.account.save(update_fields=['cash_balance'])
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10.0000'),
        )
        self.assertEqual(assessment.decision, TradeRiskDecision.BLOCK)

        decision = evaluate_trade_policy(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10.0000'),
            risk_assessment=assessment,
        )

        self.assertEqual(decision.decision, ApprovalDecisionType.HARD_BLOCK)

    def test_market_not_operable_is_hard_block(self):
        self.market.status = MarketStatus.PAUSED
        self.market.save(update_fields=['status'])

        decision = evaluate_trade_policy(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        self.assertEqual(decision.decision, ApprovalDecisionType.HARD_BLOCK)

    def test_high_existing_exposure_requires_review(self):
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

        decision = evaluate_trade_policy(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10.0000'),
            risk_assessment=assessment,
        )

        self.assertIn(decision.decision, {ApprovalDecisionType.APPROVAL_REQUIRED, ApprovalDecisionType.HARD_BLOCK})
        self.assertTrue(any(rule['code'].startswith('MARKET_EXPOSURE') for rule in decision.matched_rules))


    def test_policy_evaluation_works_for_real_read_only_market(self):
        provider = Provider.objects.create(name='Kalshi Policy Real', slug='kalshi-policy-real')
        event = Event.objects.create(provider=provider, title='Policy Real Event', slug='policy-real-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')
        market = Market.objects.create(
            provider=provider,
            event=event,
            title='Policy Real Market',
            slug='policy-real-market',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_yes_price=Decimal('52.0000'),
            current_no_price=Decimal('48.0000'),
            current_market_probability=Decimal('0.5200'),
        )

        decision = evaluate_trade_policy(
            market=market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        self.assertIn(decision.decision, {ApprovalDecisionType.AUTO_APPROVE, ApprovalDecisionType.APPROVAL_REQUIRED})
        self.assertEqual(decision.market.source_type, MarketSourceType.REAL_READ_ONLY)


class PolicyEvaluationApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_post_evaluate_trade_endpoint_returns_persisted_decision(self):
        assessment = assess_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
        )

        response = self.client.post(
            reverse('policy_engine:evaluate-trade'),
            {
                'market_id': self.market.id,
                'trade_type': 'BUY',
                'side': 'YES',
                'quantity': '2.0000',
                'risk_assessment_id': assessment.id,
                'triggered_from': 'market_detail',
                'requested_by': 'user',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['market'], self.market.id)
        self.assertEqual(payload['decision'], ApprovalDecisionType.AUTO_APPROVE)
        self.assertEqual(ApprovalDecision.objects.count(), 1)

    def test_decisions_list_endpoint_filters_recent_rows(self):
        evaluate_trade_policy(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('2.0000'))
        evaluate_trade_policy(market=self.market, trade_type='BUY', side='NO', quantity=Decimal('3.0000'))

        response = self.client.get(reverse('policy_engine:decision-list'), {'market': self.market.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertTrue(all(item['market'] == self.market.id for item in response.json()))
