from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.signals.models import MarketSignal, MockAgent, SignalRun
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class MockAgentSeedTests(TestCase):
    def test_seed_mock_agents_is_idempotent(self):
        first = seed_mock_agents()
        second = seed_mock_agents()

        self.assertEqual(first['total'], 5)
        self.assertEqual(second['total'], 5)
        self.assertEqual(MockAgent.objects.count(), 5)
        self.assertEqual(MockAgent.objects.filter(is_active=True).count(), 5)
        self.assertTrue(MockAgent.objects.filter(slug='prediction-agent').exists())

    def test_seed_mock_agents_command_outputs_summary(self):
        stdout = StringIO()

        call_command('seed_mock_agents', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Ensuring demo mock agents exist...', output)
        self.assertIn('Mock agents ready.', output)
        self.assertIn('total=5', output)


class DemoSignalGenerationTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()

    def test_generate_demo_signals_creates_signals_and_run(self):
        result = generate_demo_signals()

        self.assertEqual(result.markets_evaluated, Market.objects.count())
        self.assertGreater(MarketSignal.objects.count(), 0)
        self.assertEqual(SignalRun.objects.count(), 1)
        self.assertTrue(MarketSignal.objects.filter(agent__slug='scan-agent').exists())
        self.assertTrue(MarketSignal.objects.filter(agent__slug='risk-agent').exists())

    def test_generate_demo_signals_command_is_repeatable(self):
        stdout = StringIO()

        call_command('generate_demo_signals', stdout=stdout)
        first_count = MarketSignal.objects.count()
        call_command('generate_demo_signals', stdout=stdout)

        self.assertEqual(MarketSignal.objects.count(), first_count)
        output = stdout.getvalue()
        self.assertIn('Generating demo signals using local heuristics...', output)
        self.assertIn('Demo signals generation complete.', output)


class SignalsApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

    def test_signal_list_endpoint_returns_rows(self):
        response = self.client.get(reverse('signals:signal-list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload), 0)
        self.assertIn('market_title', payload[0])
        self.assertIn('agent', payload[0])

    def test_signal_list_filters_by_market_direction_and_actionable(self):
        response = self.client.get(
            reverse('signals:signal-list'),
            {
                'market': self.market.id,
                'direction': 'BULLISH',
                'is_actionable': 'true',
                'ordering': '-score',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        self.assertTrue(all(item['market'] == self.market.id for item in payload))
        self.assertTrue(all(item['direction'] == 'BULLISH' for item in payload))
        self.assertTrue(all(item['is_actionable'] for item in payload))

    def test_signal_detail_and_agents_endpoints_work(self):
        signal = MarketSignal.objects.first()
        detail_response = self.client.get(reverse('signals:signal-detail', kwargs={'pk': signal.pk}))
        agents_response = self.client.get(reverse('signals:signal-agent-list'))

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()['id'], signal.id)
        self.assertIn('rationale', detail_response.json())
        self.assertEqual(agents_response.status_code, 200)
        self.assertEqual(len(agents_response.json()), 5)

    def test_signal_summary_endpoint_returns_latest_run(self):
        response = self.client.get(reverse('signals:signal-summary'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['active_agents'], 5)
        self.assertGreater(payload['total_signals'], 0)
        self.assertGreaterEqual(payload['actionable_signals'], 1)
        self.assertIsNotNone(payload['latest_run'])
