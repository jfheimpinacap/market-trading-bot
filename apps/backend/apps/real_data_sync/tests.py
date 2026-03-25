from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.provider_registry import _ensure_provider_paths
from apps.real_data_sync.models import ProviderSyncRun, ProviderSyncStatus
from django.test import TestCase


class RealDataSyncServiceTests(TestCase):
    @patch('apps.markets.services.real_data_ingestion.get_provider_client')
    def test_run_provider_sync_success_persists_run_and_snapshots(self, mocked_client):
        _ensure_provider_paths()
        from provider_core.types import NormalizedMarketRecord

        class FakeClient:
            def list_markets(self, **kwargs):
                return [
                    NormalizedMarketRecord(
                        provider_name='Kalshi',
                        provider_slug='kalshi',
                        provider_market_id='KALSHI-REAL-1',
                        provider_event_id='KAL-EVT-1',
                        title='Will sync pass?',
                        category='politics',
                        status='open',
                        is_active=True,
                        market_probability=Decimal('0.5500'),
                        yes_price=Decimal('0.5500'),
                        no_price=Decimal('0.4500'),
                        liquidity=Decimal('5000.0000'),
                        volume=Decimal('2500.0000'),
                        volume_24h=Decimal('120.0000'),
                    )
                ]

        mocked_client.return_value = FakeClient()

        from apps.real_data_sync.services import run_provider_sync

        run = run_provider_sync(provider='kalshi', limit=5, triggered_from='tests')
        self.assertEqual(run.status, ProviderSyncStatus.SUCCESS)
        self.assertEqual(run.markets_seen, 1)
        self.assertEqual(run.snapshots_created, 1)

    @patch('apps.markets.services.real_data_ingestion.get_provider_client')
    def test_run_provider_sync_partial_when_record_errors(self, mocked_client):
        _ensure_provider_paths()

        class BrokenClient:
            def list_markets(self, **kwargs):
                return [type('BrokenRecord', (), {'provider_market_id': 'BROKEN-1', 'provider_event_id': None})()]

        mocked_client.return_value = BrokenClient()

        from apps.real_data_sync.services import run_provider_sync

        run = run_provider_sync(provider='kalshi', limit=1, triggered_from='tests')
        self.assertEqual(run.status, ProviderSyncStatus.PARTIAL)
        self.assertEqual(run.errors_count, 1)

    @patch('apps.real_data_sync.services.sync.ingest_provider_markets', side_effect=RuntimeError('provider down'))
    def test_run_provider_sync_failed(self, _mocked_ingest):
        from apps.real_data_sync.services import run_provider_sync

        run = run_provider_sync(provider='polymarket', triggered_from='tests')
        self.assertEqual(run.status, ProviderSyncStatus.FAILED)
        self.assertEqual(run.errors_count, 1)


class RealDataSyncApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.success_run = ProviderSyncRun.objects.create(
            provider='kalshi',
            sync_type='full',
            status='SUCCESS',
            started_at=timezone.now(),
            finished_at=timezone.now(),
            triggered_from='tests',
            markets_seen=10,
            markets_created=2,
            markets_updated=8,
            snapshots_created=10,
            errors_count=0,
            summary='ok',
        )
        ProviderSyncRun.objects.create(
            provider='polymarket',
            sync_type='active_only',
            status='FAILED',
            started_at=timezone.now(),
            finished_at=timezone.now(),
            triggered_from='tests',
            errors_count=1,
            summary='failed',
        )

    @patch('apps.real_data_sync.views.run_provider_sync')
    def test_post_run_endpoint(self, mocked_run):
        mocked_run.return_value = self.success_run
        response = self.client.post(
            reverse('real_data_sync:run'),
            data={'provider': 'kalshi', 'active_only': True, 'limit': 25, 'triggered_from': 'automation'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], self.success_run.id)

    def test_get_runs_endpoint(self):
        response = self.client.get(reverse('real_data_sync:runs'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)

    def test_status_and_summary_endpoints(self):
        status_response = self.client.get(reverse('real_data_sync:status'))
        summary_response = self.client.get(reverse('real_data_sync:summary'))

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('providers', status_response.json())
        self.assertEqual(summary_response.json()['total_runs'], 2)
