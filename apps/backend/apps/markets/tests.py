from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .demo_data import seed_demo_markets
from .models import Event, Market, MarketRule, MarketSnapshot, MarketStatus, Provider


class MarketsModelTests(TestCase):
    def test_seed_demo_markets_creates_expected_dataset(self):
        counts = seed_demo_markets()

        self.assertEqual(counts['providers'], 2)
        self.assertEqual(counts['events'], 6)
        self.assertEqual(counts['markets'], 12)
        self.assertEqual(counts['snapshots'], 72)
        self.assertEqual(counts['rules'], 6)

        self.assertEqual(Provider.objects.count(), 2)
        self.assertEqual(Event.objects.count(), 6)
        self.assertEqual(Market.objects.count(), 12)
        self.assertEqual(MarketSnapshot.objects.count(), 72)
        self.assertEqual(MarketRule.objects.count(), 6)

        open_market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.assertEqual(open_market.provider.slug, 'kalshi')
        self.assertEqual(open_market.event.slug, 'us-presidential-election-2028-demo')
        self.assertEqual(open_market.snapshots.count(), 6)
        self.assertEqual(open_market.rules.count(), 2)

    def test_seed_demo_markets_is_idempotent(self):
        first_counts = seed_demo_markets()
        second_counts = seed_demo_markets()

        self.assertEqual(first_counts, second_counts)
        self.assertEqual(Provider.objects.count(), 2)
        self.assertEqual(Event.objects.count(), 6)
        self.assertEqual(Market.objects.count(), 12)
        self.assertEqual(MarketSnapshot.objects.count(), 72)
        self.assertEqual(MarketRule.objects.count(), 6)


class MarketsManagementCommandTests(TestCase):
    def test_seed_markets_demo_command_outputs_summary(self):
        stdout = StringIO()

        call_command('seed_markets_demo', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Seeding demo markets data...', output)
        self.assertIn('Demo markets data ready.', output)
        self.assertIn('providers=2', output)
        self.assertIn('markets=12', output)
        self.assertEqual(MarketSnapshot.objects.count(), 72)


class MarketsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        seed_demo_markets()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_provider_list_endpoint_includes_counts(self):
        response = self.client.get(reverse('markets:provider-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]['event_count'], 3)
        self.assertEqual(response.json()[0]['market_count'], 6)

    def test_event_list_endpoint_supports_filters(self):
        response = self.client.get(reverse('markets:event-list'), {'provider': 'polymarket', 'category': 'technology'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['title'], 'AI Platform Launch Window 2026 Demo')
        self.assertEqual(payload[0]['market_count'], 2)

    def test_market_list_endpoint_supports_filters_search_and_ordering(self):
        response = self.client.get(
            reverse('markets:market-list'),
            {
                'provider': 'kalshi',
                'category': 'politics',
                'status': 'open',
                'is_active': 'true',
                'search': 'Candidate',
                'ordering': '-current_market_probability',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['title'], 'Will Candidate A win the 2028 election?')
        self.assertEqual(payload[0]['snapshot_count'], 6)
        self.assertIsNotNone(payload[0]['latest_snapshot_at'])

    def test_market_detail_endpoint_includes_rules_event_and_recent_snapshots(self):
        response = self.client.get(reverse('markets:market-detail', kwargs={'pk': self.market.pk}))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['id'], self.market.id)
        self.assertEqual(payload['event']['title'], 'US Presidential Election 2028 Demo')
        self.assertEqual(len(payload['rules']), 2)
        self.assertEqual(len(payload['recent_snapshots']), 5)
        self.assertEqual(payload['recent_snapshots'][0]['market_probability'], '0.5400')

    def test_market_system_summary_endpoint_returns_counts(self):
        response = self.client.get(reverse('markets:market-system-summary'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                'total_providers': 2,
                'total_events': 6,
                'total_markets': 12,
                'active_markets': 8,
                'resolved_markets': 1,
                'total_snapshots': 72,
            },
        )


class MarketSimulationTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.open_market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.resolved_market = Market.objects.get(slug='will-export-controls-tighten-before-november-2025')

    def test_simulate_markets_tick_updates_eligible_markets_and_creates_snapshots(self):
        previous_snapshot_count = MarketSnapshot.objects.count()
        previous_probability = self.open_market.current_market_probability

        stdout = StringIO()
        call_command('simulate_markets_tick', '--seed', '7', stdout=stdout)

        self.open_market.refresh_from_db()
        output = stdout.getvalue()
        self.assertIn('Simulation tick complete.', output)
        self.assertGreater(MarketSnapshot.objects.count(), previous_snapshot_count)
        self.assertNotEqual(self.open_market.current_market_probability, previous_probability)
        self.assertIn('simulation', self.open_market.metadata)

    def test_simulation_respects_basic_value_limits(self):
        call_command('simulate_markets_tick', '--seed', '11')
        market = Market.objects.get(pk=self.open_market.pk)

        self.assertGreaterEqual(market.current_market_probability, Decimal('0.0100'))
        self.assertLessEqual(market.current_market_probability, Decimal('0.9900'))
        self.assertGreaterEqual(market.current_yes_price, Decimal('0.0000'))
        self.assertGreaterEqual(market.current_no_price, Decimal('0.0000'))
        self.assertGreaterEqual(market.liquidity, Decimal('0.0000'))
        self.assertGreaterEqual(market.volume_total, self.open_market.volume_total)
        self.assertGreaterEqual(market.spread_bps, 0)

    def test_simulation_does_not_modify_terminal_markets(self):
        previous_snapshot_count = self.resolved_market.snapshots.count()
        previous_probability = self.resolved_market.current_market_probability

        call_command('simulate_markets_tick', '--seed', '3')

        self.resolved_market.refresh_from_db()
        self.assertEqual(self.resolved_market.status, MarketStatus.RESOLVED)
        self.assertEqual(self.resolved_market.current_market_probability, previous_probability)
        self.assertEqual(self.resolved_market.snapshots.count(), previous_snapshot_count)

    def test_simulate_markets_tick_dry_run_does_not_persist(self):
        previous_snapshot_count = MarketSnapshot.objects.count()
        previous_probability = self.open_market.current_market_probability

        call_command('simulate_markets_tick', '--seed', '5', '--dry-run')

        self.open_market.refresh_from_db()
        self.assertEqual(MarketSnapshot.objects.count(), previous_snapshot_count)
        self.assertEqual(self.open_market.current_market_probability, previous_probability)

    def test_simulate_markets_loop_runs_requested_iterations(self):
        stdout = StringIO()

        call_command('simulate_markets_loop', '--seed', '9', '--interval', '0', '--iterations', '2', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Tick 1:', output)
        self.assertIn('Tick 2:', output)
        self.assertIn('Simulation loop finished after 2 tick(s).', output)
