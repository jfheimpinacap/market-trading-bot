from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Event, Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.models import (
    PaperAccount,
    PaperPortfolioSnapshot,
    PaperPosition,
    PaperPositionStatus,
    PaperTrade,
)
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.paper_trading.services.valuation import PaperTradingRejectionError, revalue_account


class PaperTradingAccountCommandTests(TestCase):
    def test_seed_paper_account_command_is_idempotent(self):
        stdout = StringIO()

        call_command('seed_paper_account', stdout=stdout)
        call_command('seed_paper_account', stdout=stdout)

        self.assertEqual(PaperAccount.objects.count(), 1)
        account = PaperAccount.objects.get()
        self.assertEqual(account.slug, 'demo-paper-account')
        self.assertEqual(account.cash_balance, Decimal('10000.00'))
        output = stdout.getvalue()
        self.assertIn('Ensuring demo paper trading account exists...', output)
        self.assertIn('Demo paper account', output)


class PaperTradingServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.real_provider = Provider.objects.create(name='Kalshi Real', slug='kalshi-real')
        self.real_event = Event.objects.create(provider=self.real_provider, title='Real Event', slug='real-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')

    def test_buy_yes_trade_updates_cash_position_and_trade(self):
        result = execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10'),
            account=self.account,
        )

        self.account.refresh_from_db()
        result.position.refresh_from_db()
        self.assertEqual(PaperTrade.objects.count(), 1)
        self.assertEqual(result.trade.price, self.market.current_yes_price)
        self.assertEqual(result.position.quantity, Decimal('10.0000'))
        self.assertEqual(result.position.average_entry_price, self.market.current_yes_price)
        self.assertEqual(self.account.cash_balance, Decimal('9460.00'))
        self.assertEqual(self.account.equity, Decimal('10000.00'))
        self.assertEqual(PaperPortfolioSnapshot.objects.count(), 1)

    def test_buy_trade_rejected_when_balance_is_insufficient(self):
        self.account.cash_balance = Decimal('1.00')
        self.account.save(update_fields=['cash_balance'])

        with self.assertRaises(PaperTradingRejectionError):
            execute_paper_trade(
                market=self.market,
                trade_type='BUY',
                side='YES',
                quantity=Decimal('10'),
                account=self.account,
            )

        self.assertEqual(PaperTrade.objects.count(), 0)

    def test_sell_trade_reduces_and_closes_position(self):
        execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10'),
            account=self.account,
        )
        self.market.current_yes_price = Decimal('70.0000')
        self.market.save(update_fields=['current_yes_price'])

        execute_paper_trade(
            market=self.market,
            trade_type='SELL',
            side='YES',
            quantity=Decimal('10'),
            account=self.account,
        )

        position = PaperPosition.objects.get(account=self.account, market=self.market, side='YES')
        self.account.refresh_from_db()
        self.assertEqual(position.quantity, Decimal('0.0000'))
        self.assertEqual(position.status, PaperPositionStatus.CLOSED)
        self.assertEqual(position.realized_pnl, Decimal('160.00'))
        self.assertEqual(self.account.cash_balance, Decimal('10160.00'))
        self.assertEqual(self.account.realized_pnl, Decimal('160.00'))

    def test_revalue_account_updates_unrealized_pnl(self):
        execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('10'),
            account=self.account,
        )
        self.market.current_yes_price = Decimal('64.0000')
        self.market.save(update_fields=['current_yes_price'])

        revalue_account(self.account)
        position = PaperPosition.objects.get(account=self.account, market=self.market, side='YES')
        self.account.refresh_from_db()
        self.assertEqual(position.unrealized_pnl, Decimal('100.00'))
        self.assertEqual(self.account.unrealized_pnl, Decimal('100.00'))
        self.assertEqual(self.account.equity, Decimal('10100.00'))


    def test_buy_trade_allowed_on_real_read_only_market_with_pricing(self):
        real_market = Market.objects.create(
            provider=self.real_provider,
            event=self.real_event,
            title='Real market for paper trading',
            slug='real-market-paper',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_market_probability=Decimal('0.6200'),
            current_yes_price=Decimal('62.0000'),
            current_no_price=Decimal('38.0000'),
        )

        result = execute_paper_trade(
            market=real_market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('2.0000'),
            account=self.account,
        )

        self.assertEqual(result.trade.market.source_type, MarketSourceType.REAL_READ_ONLY)
        self.assertEqual(result.trade.metadata['execution_mode'], 'paper_demo_only')
        self.assertTrue(result.trade.metadata['is_real_data'])

    def test_real_market_without_valid_price_is_rejected(self):
        real_market = Market.objects.create(
            provider=self.real_provider,
            event=self.real_event,
            title='Real market missing price',
            slug='real-market-no-price',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_market_probability=None,
            current_yes_price=None,
            current_no_price=None,
        )

        with self.assertRaisesRegex(Exception, 'enough pricing data'):
            execute_paper_trade(
                market=real_market,
                trade_type='BUY',
                side='YES',
                quantity=Decimal('1.0000'),
                account=self.account,
            )

    def test_terminal_real_market_is_blocked(self):
        real_market = Market.objects.create(
            provider=self.real_provider,
            event=self.real_event,
            title='Real market terminal',
            slug='real-market-terminal',
            status=MarketStatus.RESOLVED,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_yes_price=Decimal('55.0000'),
            current_no_price=Decimal('45.0000'),
        )

        with self.assertRaisesRegex(Exception, 'terminal and cannot be used for paper execution'):
            execute_paper_trade(
                market=real_market,
                trade_type='BUY',
                side='YES',
                quantity=Decimal('1.0000'),
                account=self.account,
            )



class PaperTradingApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.real_provider = Provider.objects.create(name='Kalshi Real', slug='kalshi-real')
        self.real_event = Event.objects.create(provider=self.real_provider, title='Real Event', slug='real-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')

    def test_get_account_positions_and_trades_endpoints(self):
        account = get_active_account()
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5'), account=account)

        account_response = self.client.get(reverse('paper_trading:paper-account'))
        positions_response = self.client.get(reverse('paper_trading:paper-position-list'))
        trades_response = self.client.get(reverse('paper_trading:paper-trade-list-create'))
        summary_response = self.client.get(reverse('paper_trading:paper-summary'))

        self.assertEqual(account_response.status_code, 200)
        self.assertEqual(positions_response.status_code, 200)
        self.assertEqual(trades_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(account_response.json()['slug'], 'demo-paper-account')
        self.assertEqual(len(positions_response.json()), 1)
        self.assertEqual(len(trades_response.json()), 1)
        self.assertEqual(summary_response.json()['open_positions_count'], 1)

    def test_post_trade_endpoint_executes_trade(self):
        response = self.client.post(
            reverse('paper_trading:paper-trade-list-create'),
            {
                'market_id': self.market.id,
                'trade_type': 'BUY',
                'side': 'YES',
                'quantity': '10.0000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['trade']['trade_type'], 'BUY')
        self.assertEqual(payload['position']['quantity'], '10.0000')
        self.assertEqual(payload['account']['cash_balance'], '9460.00')

    def test_post_trade_endpoint_returns_validation_error_when_insufficient_balance(self):
        account = get_active_account()
        account.cash_balance = Decimal('1.00')
        account.save(update_fields=['cash_balance'])

        response = self.client.post(
            reverse('paper_trading:paper-trade-list-create'),
            {
                'market_id': self.market.id,
                'trade_type': 'BUY',
                'side': 'YES',
                'quantity': '10.0000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.json())


    def test_post_trade_endpoint_accepts_real_read_only_market(self):
        provider = Provider.objects.create(name='PM Real', slug='pm-real')
        event = Event.objects.create(provider=provider, title='Real API event', slug='real-api-event', source_type=MarketSourceType.REAL_READ_ONLY, status='open')
        market = Market.objects.create(
            provider=provider,
            event=event,
            title='Real API market',
            slug='real-api-market',
            status=MarketStatus.OPEN,
            is_active=True,
            source_type=MarketSourceType.REAL_READ_ONLY,
            current_yes_price=Decimal('51.0000'),
            current_no_price=Decimal('49.0000'),
        )

        response = self.client.post(
            reverse('paper_trading:paper-trade-list-create'),
            {
                'market_id': market.id,
                'trade_type': 'BUY',
                'side': 'YES',
                'quantity': '1.0000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload['trade']['is_real_data'])
        self.assertEqual(payload['trade']['execution_mode'], 'paper_demo_only')
