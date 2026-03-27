from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.execution_simulator.models import PaperOrder, PaperOrderCreatedFrom, PaperOrderStatus
from apps.execution_simulator.services import create_order, run_execution_lifecycle
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.models import PaperPositionStatus
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account


class ExecutionSimulatorServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.account = get_active_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.market.liquidity = Decimal('20000')
        self.market.spread_bps = 60
        self.market.save(update_fields=['liquidity', 'spread_bps'])

    def test_full_fill(self):
        order = create_order(
            market=self.market,
            side='BUY_YES',
            requested_quantity=Decimal('2.0000'),
            created_from=PaperOrderCreatedFrom.MANUAL,
            policy_profile='optimistic_paper',
        )
        run_execution_lifecycle()
        order.refresh_from_db()

        self.assertEqual(order.status, PaperOrderStatus.FILLED)
        self.assertEqual(order.remaining_quantity, Decimal('0.0000'))

    def test_partial_fill(self):
        self.market.liquidity = Decimal('3000')
        self.market.spread_bps = 200
        self.market.save(update_fields=['liquidity', 'spread_bps'])
        order = create_order(
            market=self.market,
            side='BUY_YES',
            requested_quantity=Decimal('2.0000'),
            created_from=PaperOrderCreatedFrom.MANUAL,
            policy_profile='balanced_paper',
        )
        run_execution_lifecycle()
        order.refresh_from_db()
        self.assertEqual(order.status, PaperOrderStatus.PARTIALLY_FILLED)
        self.assertGreater(order.remaining_quantity, Decimal('0'))

    def test_no_fill(self):
        self.market.liquidity = Decimal('100')
        self.market.spread_bps = 400
        self.market.save(update_fields=['liquidity', 'spread_bps'])
        order = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('1.0000'))
        run_execution_lifecycle()
        order.refresh_from_db()
        self.assertEqual(order.status, PaperOrderStatus.OPEN)

    def test_cancel_and_expire(self):
        self.market.liquidity = Decimal('100')
        self.market.spread_bps = 500
        self.market.save(update_fields=['liquidity', 'spread_bps'])
        cancel_order = create_order(
            market=self.market,
            side='BUY_YES',
            requested_quantity=Decimal('1.0000'),
            metadata={'cancel_after_n_cycles': 1},
        )
        expire_order = create_order(
            market=self.market,
            side='BUY_YES',
            requested_quantity=Decimal('1.0000'),
            metadata={'expires_at': timezone.now() - timedelta(minutes=1)},
        )
        run_execution_lifecycle()
        cancel_order.refresh_from_db()
        expire_order.refresh_from_db()
        self.assertEqual(cancel_order.status, PaperOrderStatus.CANCELLED)
        self.assertEqual(expire_order.status, PaperOrderStatus.EXPIRED)

    def test_close_reduce_orders_update_portfolio(self):
        entry = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('4.0000'), policy_profile='optimistic_paper')
        run_execution_lifecycle()
        entry.refresh_from_db()
        self.assertEqual(entry.status, PaperOrderStatus.FILLED)

        reduce_order = create_order(
            market=self.market,
            side='REDUCE',
            requested_quantity=Decimal('1.0000'),
            created_from=PaperOrderCreatedFrom.POSITION_MANAGER,
            metadata={'position_side': 'YES'},
            policy_profile='optimistic_paper',
        )
        run_execution_lifecycle()
        reduce_order.refresh_from_db()
        self.assertEqual(reduce_order.status, PaperOrderStatus.FILLED)
        position = self.account.positions.get(market=self.market, side='YES')
        self.assertEqual(position.status, PaperPositionStatus.OPEN)
        self.assertEqual(position.quantity, Decimal('3.0000'))


class ExecutionSimulatorApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.market.liquidity = Decimal('18000')
        self.market.spread_bps = 80
        self.market.save(update_fields=['liquidity', 'spread_bps'])

    def test_endpoints(self):
        create_response = self.client.post(
            reverse('execution_simulator:create-order'),
            {
                'market_id': self.market.id,
                'side': 'BUY_YES',
                'requested_quantity': '2.0000',
                'created_from': 'manual',
                'policy_profile': 'optimistic_paper',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        order_id = create_response.json()['order']['id']

        run_response = self.client.post(reverse('execution_simulator:run-lifecycle'), {'open_only': True}, format='json')
        self.assertEqual(run_response.status_code, 201)

        orders_response = self.client.get(reverse('execution_simulator:orders'))
        fills_response = self.client.get(reverse('execution_simulator:fills'))
        detail_response = self.client.get(reverse('execution_simulator:order-detail', kwargs={'pk': order_id}))
        summary_response = self.client.get(reverse('execution_simulator:summary'))

        self.assertEqual(orders_response.status_code, 200)
        self.assertEqual(fills_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreaterEqual(summary_response.json()['total_orders'], 1)
        self.assertGreaterEqual(len(orders_response.json()), 1)
        self.assertGreaterEqual(PaperOrder.objects.count(), 1)
