from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.allocation_engine.models import AllocationDecisionType, AllocationRun
from apps.allocation_engine.services import AllocationConfig, evaluate_allocation
from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningScopeType
from apps.markets.models import Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.models import PaperPosition, PaperPositionStatus
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import ProposalDirection, ProposalTradeType, ProposalStatus, TradeProposal
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus, ProviderSyncType
from apps.risk_demo.models import TradeRiskDecision


class AllocationEngineTests(TestCase):
    def setUp(self):
        self.account, _ = ensure_demo_account()
        self.account.cash_balance = Decimal('1000.00')
        self.account.save(update_fields=['cash_balance', 'updated_at'])
        self.provider = Provider.objects.create(name='Kalshi', slug='kalshi')
        self.market_a = Market.objects.create(
            provider=self.provider,
            title='Market A',
            slug='market-a',
            source_type=MarketSourceType.DEMO,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('50.0'),
            liquidity=Decimal('2000'),
            volume_24h=Decimal('2000'),
        )
        self.market_b = Market.objects.create(
            provider=self.provider,
            title='Market B',
            slug='market-b',
            source_type=MarketSourceType.DEMO,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('55.0'),
            liquidity=Decimal('2000'),
            volume_24h=Decimal('2000'),
        )
        ProviderSyncRun.objects.create(
            provider='kalshi',
            sync_type=ProviderSyncType.ACTIVE_ONLY,
            status=ProviderSyncStatus.SUCCESS,
            started_at=timezone.now() - timedelta(minutes=2),
            finished_at=timezone.now() - timedelta(minutes=1),
        )

    def _proposal(self, *, market, score: str, confidence: str, quantity: str = '4.0000', policy=ApprovalDecisionType.AUTO_APPROVE):
        return TradeProposal.objects.create(
            market=market,
            paper_account=self.account,
            proposal_status=ProposalStatus.ACTIVE,
            direction=ProposalDirection.BUY_YES,
            proposal_score=Decimal(score),
            confidence=Decimal(confidence),
            headline=f'Proposal {market.title} {score}',
            thesis='Test thesis',
            suggested_trade_type=ProposalTradeType.BUY,
            suggested_side='YES',
            suggested_quantity=Decimal(quantity),
            suggested_price_reference=Decimal('50.0'),
            risk_decision=TradeRiskDecision.APPROVE,
            policy_decision=policy,
            approval_required=policy == ApprovalDecisionType.APPROVAL_REQUIRED,
            is_actionable=True,
        )

    def test_ranking_prefers_higher_score(self):
        high = self._proposal(market=self.market_a, score='85.00', confidence='0.80')
        low = self._proposal(market=self.market_b, score='60.00', confidence='0.50')

        result = evaluate_allocation(proposals=[low, high], config=AllocationConfig(max_executions_per_run=2), persist=False)
        self.assertEqual(result['details'][0]['proposal'].id, high.id)

    def test_reduces_quantity_when_cash_insufficient(self):
        proposal = self._proposal(market=self.market_a, score='80.00', confidence='0.70', quantity='30.0000')
        result = evaluate_allocation(proposals=[proposal], config=AllocationConfig(reserve_cash_amount=Decimal('990.00')), persist=False)
        self.assertEqual(result['details'][0]['decision'], AllocationDecisionType.REDUCED)
        self.assertGreater(result['details'][0]['final_allocated_quantity'], Decimal('0.0000'))

    def test_excludes_for_existing_exposure(self):
        PaperPosition.objects.create(
            account=self.account,
            market=self.market_a,
            side='YES',
            quantity=Decimal('4.0000'),
            average_entry_price=Decimal('60.0'),
            cost_basis=Decimal('350.00'),
            market_value=Decimal('380.00'),
            status=PaperPositionStatus.OPEN,
        )
        proposal = self._proposal(market=self.market_a, score='88.00', confidence='0.90', quantity='8.0000')
        result = evaluate_allocation(
            proposals=[proposal],
            config=AllocationConfig(max_allocation_per_market=Decimal('300.00'), reserve_cash_amount=Decimal('0.00')),
            persist=False,
        )
        self.assertEqual(result['details'][0]['decision'], AllocationDecisionType.REJECTED)

    def test_excludes_hard_block(self):
        proposal = self._proposal(market=self.market_a, score='90.00', confidence='0.90', policy=ApprovalDecisionType.HARD_BLOCK)
        result = evaluate_allocation(proposals=[proposal], persist=False)
        self.assertEqual(result['details'][0]['decision'], AllocationDecisionType.REJECTED)

    def test_selects_top_n(self):
        first = self._proposal(market=self.market_a, score='90.00', confidence='0.90')
        second = self._proposal(market=self.market_b, score='70.00', confidence='0.60')
        result = evaluate_allocation(proposals=[first, second], config=AllocationConfig(max_executions_per_run=1), persist=False)
        selected = [item for item in result['details'] if item['decision'] in {AllocationDecisionType.SELECTED, AllocationDecisionType.REDUCED}]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]['proposal'].id, first.id)

    def test_endpoints_work(self):
        self._proposal(market=self.market_a, score='88.00', confidence='0.80')
        client = APIClient()
        self.assertEqual(client.post(reverse('allocation_engine:evaluate'), {'scope_type': 'mixed'}, format='json').status_code, 200)
        run_response = client.post(reverse('allocation_engine:run'), {'scope_type': 'mixed', 'triggered_from': 'manual'}, format='json')
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(client.get(reverse('allocation_engine:runs')).status_code, 200)
        run = AllocationRun.objects.order_by('-id').first()
        self.assertEqual(client.get(reverse('allocation_engine:run-detail', kwargs={'pk': run.id})).status_code, 200)

    def test_learning_penalty_applies(self):
        LearningAdjustment.objects.create(
            adjustment_type=LearningAdjustmentType.CONFIDENCE_BIAS,
            scope_type=LearningScopeType.GLOBAL,
            scope_key='global',
            magnitude=Decimal('-0.1000'),
            reason='test',
            is_active=True,
        )
        proposal = self._proposal(market=self.market_a, score='80.00', confidence='0.80')
        result = evaluate_allocation(proposals=[proposal], persist=False)
        self.assertIn('learning_penalty:confidence_bias:global:global', result['details'][0]['rationale'])
