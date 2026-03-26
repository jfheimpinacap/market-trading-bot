from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.models import Market
from apps.markets.demo_data import seed_demo_markets
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.position_manager.models import PositionLifecycleStatus
from apps.position_manager.services import run_position_lifecycle
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.runtime_governor.models import RuntimeMode
from apps.runtime_governor.services import set_runtime_mode
from apps.risk_agent.services import run_position_watch


class PositionLifecycleTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.account = get_active_account()
        self.market = Market.objects.order_by('id').first()
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('12.0000'))

    def _prepare_prediction(self):
        return score_market_prediction(market=self.market, triggered_by='test').score

    def test_hold_decision_basic(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_SEMI_AUTO, set_by='system', rationale='test')
        self._prepare_prediction()
        run = run_position_lifecycle(metadata={'scenario': 'hold'})
        self.assertEqual(run.status, 'SUCCESS')
        self.assertIn(run.decisions.first().status, {PositionLifecycleStatus.HOLD, PositionLifecycleStatus.BLOCK_ADD, PositionLifecycleStatus.REDUCE})

    def test_review_required_in_observe_only_runtime(self):
        set_runtime_mode(requested_mode=RuntimeMode.OBSERVE_ONLY, set_by='system', rationale='test')
        self._prepare_prediction()
        run = run_position_lifecycle(metadata={'scenario': 'observe_only'})
        self.assertEqual(run.decisions.first().status, PositionLifecycleStatus.REVIEW_REQUIRED)

    def test_reduce_decision_for_partial_deterioration(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_SEMI_AUTO, set_by='system', rationale='test')
        position = self.account.positions.filter(status='OPEN').first()
        position.metadata = {**position.metadata, 'entry_market_probability': '0.6000'}
        position.save(update_fields=['metadata', 'updated_at'])
        self.market.current_market_probability = Decimal('0.5300')
        self.market.save(update_fields=['current_market_probability', 'updated_at'])
        run = run_position_lifecycle(metadata={'scenario': 'reduce'})
        self.assertEqual(run.decisions.first().status, PositionLifecycleStatus.REDUCE)

    def test_close_decision_when_thesis_breaks(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_AUTO, set_by='system', rationale='test')
        position = self.account.positions.filter(status='OPEN').first()
        position.metadata = {**position.metadata, 'entry_market_probability': '0.8200'}
        position.save(update_fields=['metadata', 'updated_at'])
        self.market.current_market_probability = Decimal('0.5000')
        self.market.save(update_fields=['current_market_probability', 'updated_at'])
        run = run_position_lifecycle(metadata={'scenario': 'close'})
        self.assertEqual(run.decisions.first().status, PositionLifecycleStatus.CLOSE)

    def test_watch_high_severity_can_trigger_close_or_review(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_AUTO, set_by='system', rationale='test')
        position = self.account.positions.filter(status='OPEN').first()
        position.unrealized_pnl = Decimal('-220.00')
        position.save(update_fields=['unrealized_pnl', 'updated_at'])
        run_position_watch(metadata={'test': True})
        self._prepare_prediction()
        run = run_position_lifecycle(metadata={'scenario': 'high_watch'})
        self.assertIn(run.decisions.first().status, {PositionLifecycleStatus.CLOSE, PositionLifecycleStatus.REVIEW_REQUIRED})

    def test_endpoints(self):
        client = APIClient()
        response = client.post(reverse('position_manager:run-lifecycle'), {}, format='json')
        self.assertEqual(response.status_code, 201)
        run_id = response.json()['lifecycle_run']['id']

        self.assertEqual(client.get(reverse('position_manager:lifecycle-runs')).status_code, 200)
        self.assertEqual(client.get(reverse('position_manager:lifecycle-run-detail', kwargs={'pk': run_id})).status_code, 200)
        self.assertEqual(client.get(reverse('position_manager:decisions')).status_code, 200)
        self.assertEqual(client.get(reverse('position_manager:summary')).status_code, 200)
