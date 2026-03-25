from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.models import Market, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus, ProviderSyncType
from apps.real_market_ops.models import RealScopeConfig
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals
from apps.real_market_ops.services import RunOptions, evaluate_real_market_eligibility, run_real_market_operation
from apps.safety_guard.services import disable_kill_switch, enable_kill_switch


class RealMarketOpsTests(TestCase):
    def setUp(self):
        ensure_demo_account()
        seed_mock_agents()
        self.provider = Provider.objects.create(name='Kalshi', slug='kalshi', is_active=True)
        self.market = Market.objects.create(
            provider=self.provider,
            title='Will it rain tomorrow?',
            slug='rain-tomorrow',
            source_type=MarketSourceType.REAL_READ_ONLY,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('55.0'),
            current_no_price=Decimal('45.0'),
            liquidity=Decimal('1000'),
            volume_24h=Decimal('500'),
            metadata={'paper_tradable': True},
        )
        ProviderSyncRun.objects.create(
            provider='kalshi',
            sync_type=ProviderSyncType.ACTIVE_ONLY,
            status=ProviderSyncStatus.SUCCESS,
            started_at=timezone.now() - timedelta(minutes=2),
            finished_at=timezone.now() - timedelta(minutes=1),
        )
        ProviderSyncRun.objects.create(
            provider='polymarket',
            sync_type=ProviderSyncType.ACTIVE_ONLY,
            status=ProviderSyncStatus.SUCCESS,
            started_at=timezone.now() - timedelta(minutes=2),
            finished_at=timezone.now() - timedelta(minutes=1),
        )
        generate_demo_signals()
        RealScopeConfig.objects.update_or_create(
            id=1,
            defaults={
                'enabled': True,
                'provider_scope': 'kalshi',
                'max_real_markets_per_cycle': 5,
                'max_real_auto_trades_per_cycle': 1,
                'require_fresh_sync': True,
                'stale_data_blocks_execution': True,
                'degraded_provider_blocks_execution': True,
                'min_liquidity_threshold': Decimal('10'),
                'min_volume_threshold': Decimal('10'),
            },
        )

    def test_eligibility_selects_real_markets(self):
        snapshot = evaluate_real_market_eligibility()
        self.assertEqual(snapshot.counters['markets_eligible'], 1)
        self.assertEqual(snapshot.eligible[0].id, self.market.id)

    def test_eligibility_excludes_stale_provider(self):
        stale_run = ProviderSyncRun.objects.filter(provider='kalshi').order_by('-id').first()
        stale_run.started_at = timezone.now() - timedelta(minutes=90)
        stale_run.save(update_fields=['started_at', 'updated_at'])

        snapshot = evaluate_real_market_eligibility()
        self.assertEqual(snapshot.counters['markets_eligible'], 0)
        self.assertGreaterEqual(snapshot.counters['skipped_stale_count'], 1)

    def test_eligibility_excludes_no_pricing(self):
        self.market.current_yes_price = None
        self.market.current_no_price = None
        self.market.current_market_probability = None
        self.market.save(update_fields=['current_yes_price', 'current_no_price', 'current_market_probability', 'updated_at'])

        snapshot = evaluate_real_market_eligibility()
        self.assertEqual(snapshot.counters['markets_eligible'], 0)
        self.assertGreaterEqual(snapshot.counters['skipped_no_pricing_count'], 1)

    def test_eligibility_excludes_low_liquidity(self):
        self.market.liquidity = Decimal('1')
        self.market.volume_24h = Decimal('1')
        self.market.save(update_fields=['liquidity', 'volume_24h', 'updated_at'])

        snapshot = evaluate_real_market_eligibility()
        self.assertEqual(snapshot.counters['markets_eligible'], 0)
        self.assertEqual(snapshot.excluded[0]['reasons'].count('low_liquidity'), 1)

    def test_run_successful_with_eligible_market(self):
        run = run_real_market_operation(options=RunOptions(execute_auto=False, triggered_from='manual'))
        self.assertIn(run.status, ['SUCCESS', 'PARTIAL'])
        self.assertEqual(run.markets_eligible, 1)
        self.assertGreaterEqual(len(run.details.get('results', [])), 1)

    def test_run_skipped_when_scope_disabled(self):
        config = RealScopeConfig.objects.first()
        config.enabled = False
        config.save(update_fields=['enabled', 'updated_at'])
        run = run_real_market_operation(options=RunOptions(execute_auto=True, triggered_from='manual'))
        self.assertEqual(run.status, 'SKIPPED')
        disable_kill_switch()


    def test_run_blocked_by_safety(self):
        enable_kill_switch()
        run = run_real_market_operation(options=RunOptions(execute_auto=True, triggered_from='manual'))
        self.assertEqual(run.status, 'SKIPPED')
        disable_kill_switch()

    def test_endpoints_work(self):
        client = APIClient()
        self.assertEqual(client.post(reverse('real_market_ops:evaluate'), {}, format='json').status_code, 200)
        self.assertEqual(client.post(reverse('real_market_ops:run'), {'triggered_from': 'automation'}, format='json').status_code, 200)
        self.assertEqual(client.get(reverse('real_market_ops:runs')).status_code, 200)
        self.assertEqual(client.get(reverse('real_market_ops:status')).status_code, 200)
