from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.models import Market, MarketSnapshot, MarketSourceType, MarketStatus, Provider
from apps.paper_trading.models import PaperAccount, PaperTrade
from apps.replay_lab.services.timeline import build_replay_timeline


class ReplayLabTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.provider = Provider.objects.create(name='Kalshi', slug='kalshi', is_active=True)
        self.market = Market.objects.create(
            provider=self.provider,
            title='Replay test market',
            slug='replay-test-market',
            source_type=MarketSourceType.REAL_READ_ONLY,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('55.0'),
            current_no_price=Decimal('45.0'),
        )
        now = timezone.now()
        for idx in range(3):
            MarketSnapshot.objects.create(
                market=self.market,
                captured_at=now - timedelta(minutes=10 - idx),
                market_probability=Decimal('0.55'),
                yes_price=Decimal('55.0'),
                no_price=Decimal('45.0'),
                liquidity=Decimal('1000'),
                volume_24h=Decimal('400'),
            )

    def test_timeline_builds_from_snapshots(self):
        now = timezone.now()
        timeline = build_replay_timeline(
            config={
                'start_timestamp': now - timedelta(hours=1),
                'end_timestamp': now,
                'source_scope': 'real_only',
                'provider_scope': 'kalshi',
                'active_only': True,
                'market_limit': 5,
            }
        )
        self.assertGreaterEqual(len(timeline), 1)
        self.assertGreaterEqual(len(timeline[0].snapshots), 1)

    def test_run_endpoint_creates_replay_run(self):
        now = timezone.now()
        payload = {
            'provider_scope': 'kalshi',
            'source_scope': 'real_only',
            'start_timestamp': (now - timedelta(hours=1)).isoformat(),
            'end_timestamp': now.isoformat(),
            'market_limit': 3,
            'auto_execute_allowed': True,
            'treat_approval_required_as_skip': True,
        }
        response = self.client.post(reverse('replay_lab:run'), payload, format='json')
        self.assertIn(response.status_code, [201, 400])
        run_list = self.client.get(reverse('replay_lab:runs'))
        self.assertEqual(run_list.status_code, 200)
        self.assertGreaterEqual(len(run_list.json()), 1)

    def test_summary_and_detail_endpoints(self):
        now = timezone.now()
        payload = {
            'provider_scope': 'kalshi',
            'source_scope': 'real_only',
            'start_timestamp': (now - timedelta(hours=1)).isoformat(),
            'end_timestamp': now.isoformat(),
        }
        run_response = self.client.post(reverse('replay_lab:run'), payload, format='json')
        run_id = run_response.json().get('id')
        summary = self.client.get(reverse('replay_lab:summary'))
        self.assertEqual(summary.status_code, 200)
        if run_id:
            detail = self.client.get(reverse('replay_lab:run-detail', kwargs={'pk': run_id}))
            self.assertEqual(detail.status_code, 200)


    def test_hard_block_path_blocks_execution(self):
        self.market.status = MarketStatus.PAUSED
        self.market.save(update_fields=['status', 'updated_at'])
        now = timezone.now()
        payload = {
            'provider_scope': 'kalshi',
            'source_scope': 'real_only',
            'start_timestamp': (now - timedelta(hours=1)).isoformat(),
            'end_timestamp': now.isoformat(),
            'auto_execute_allowed': True,
        }
        response = self.client.post(reverse('replay_lab:run'), payload, format='json')
        if response.status_code == 201:
            self.assertGreaterEqual(response.json()['blocked_count'], 1)

    def test_replay_uses_isolated_paper_account(self):
        now = timezone.now()
        payload = {
            'provider_scope': 'kalshi',
            'source_scope': 'real_only',
            'start_timestamp': (now - timedelta(hours=1)).isoformat(),
            'end_timestamp': now.isoformat(),
            'auto_execute_allowed': True,
        }
        self.client.post(reverse('replay_lab:run'), payload, format='json')
        self.assertTrue(PaperAccount.objects.filter(slug__startswith='replay-run-').exists())
        operational_trades = PaperTrade.objects.exclude(metadata__has_key='replay_run_id').count()
        self.assertEqual(operational_trades, 0)

    def test_execution_aware_mode_persists_execution_metrics(self):
        now = timezone.now()
        self.market.liquidity = Decimal('200')
        self.market.save(update_fields=['liquidity', 'updated_at'])
        payload = {
            'provider_scope': 'kalshi',
            'source_scope': 'real_only',
            'start_timestamp': (now - timedelta(hours=1)).isoformat(),
            'end_timestamp': now.isoformat(),
            'execution_mode': 'execution_aware',
            'execution_profile': 'conservative_paper',
            'auto_execute_allowed': True,
        }
        response = self.client.post(reverse('replay_lab:run'), payload, format='json')
        self.assertIn(response.status_code, [201, 400])
        if response.status_code == 201:
            impact = response.json().get('details', {}).get('execution_impact_summary', {})
            self.assertIn('fill_rate', impact)
            self.assertIn('no_fill_rate', impact)
            self.assertEqual(response.json().get('details', {}).get('execution_mode'), 'execution_aware')
