from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Event, Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import ProposalDirection, TradeProposal
from apps.proposal_engine.services import generate_trade_proposal
from apps.signals.models import MarketSignal, SignalDirection
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class ProposalEngineServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_generates_reasonable_buy_yes_proposal(self):
        proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='market_detail')

        self.assertEqual(proposal.direction, ProposalDirection.BUY_YES)
        self.assertEqual(proposal.suggested_trade_type, 'BUY')
        self.assertEqual(proposal.suggested_side, 'YES')
        self.assertGreater(proposal.suggested_quantity, Decimal('0.0000'))

    def test_generates_hold_or_avoid_when_signals_are_not_aligned(self):
        MarketSignal.objects.filter(market=self.market).update(direction=SignalDirection.NEUTRAL, is_actionable=False)

        proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='signals')

        self.assertIn(proposal.direction, {ProposalDirection.HOLD, ProposalDirection.AVOID})
        self.assertEqual(proposal.suggested_trade_type, 'HOLD')

    def test_policy_hard_block_makes_proposal_not_actionable(self):
        self.account.cash_balance = Decimal('0.50')
        self.account.save(update_fields=['cash_balance'])

        proposal = generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='dashboard')

        self.assertEqual(proposal.policy_decision, ApprovalDecisionType.HARD_BLOCK)
        self.assertFalse(proposal.is_actionable)

    def test_suggested_quantity_reduces_when_existing_exposure_is_high(self):
        proposal_without_exposure = generate_trade_proposal(market=self.market, paper_account=self.account)

        execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('60.0000'),
            account=self.account,
        )
        proposal_with_exposure = generate_trade_proposal(market=self.market, paper_account=self.account)

        self.assertGreaterEqual(proposal_without_exposure.suggested_quantity, proposal_with_exposure.suggested_quantity)


    def test_proposal_generation_works_for_real_read_only_market(self):
        provider = Provider.objects.create(name='Kalshi Proposal Real', slug='kalshi-proposal-real')
        event = Event.objects.create(provider=provider, title='Proposal Real Event', slug='proposal-real-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')
        market = Market.objects.create(
            provider=provider,
            event=event,
            title='Proposal Real Market',
            slug='proposal-real-market',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_yes_price=Decimal('61.0000'),
            current_no_price=Decimal('39.0000'),
            current_market_probability=Decimal('0.6100'),
        )

        proposal = generate_trade_proposal(market=market, paper_account=self.account, triggered_from='market_detail')

        self.assertEqual(proposal.market.source_type, MarketSourceType.REAL_READ_ONLY)
        self.assertIn(proposal.direction, [choice.value for choice in ProposalDirection])


class ProposalEngineApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.account, _ = ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_generate_endpoint_persists_and_returns_proposal(self):
        response = self.client.post(
            reverse('proposal_engine:proposal-generate'),
            {
                'market_id': self.market.id,
                'paper_account_id': self.account.id,
                'triggered_from': 'market_detail',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()['proposal']
        self.assertEqual(payload['market'], self.market.id)
        self.assertIn(payload['direction'], [choice.value for choice in ProposalDirection])
        self.assertEqual(TradeProposal.objects.count(), 1)

    def test_list_endpoint_returns_generated_proposals(self):
        generate_trade_proposal(market=self.market, paper_account=self.account)
        generate_trade_proposal(market=self.market, paper_account=self.account, triggered_from='signals')

        response = self.client.get(reverse('proposal_engine:proposal-list'), {'market': self.market.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item['market'] == self.market.id for item in payload))
