from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.agents.models import AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.prediction_agent.models import PredictionScore
from apps.research_agent.models import ResearchCandidate


class AgentOrchestrationApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()

    def _seed_candidate(self):
        market = Market.objects.filter(is_active=True).order_by('id').first()
        self.assertIsNotNone(market)
        candidate, _ = ResearchCandidate.objects.get_or_create(
            market=market,
            defaults={
                'short_thesis': 'Narrative divergence test candidate',
                'priority': '92.00',
            },
        )
        return candidate

    def test_agents_endpoint_registers_default_agents(self):
        response = self.client.get(reverse('agents:agent-list'))

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 5)
        self.assertGreaterEqual(AgentDefinition.objects.count(), 5)

    def test_run_research_prediction_pipeline_creates_runs_and_handoffs(self):
        self._seed_candidate()

        response = self.client.post(
            reverse('agents:run-pipeline'),
            {
                'pipeline_type': 'research_to_prediction',
                'triggered_from': 'manual',
                'payload': {'candidate_limit': 3},
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['pipeline_type'], 'research_to_prediction')
        self.assertIn(payload['status'], ['SUCCESS', 'PARTIAL'], msg=str(payload))
        self.assertGreaterEqual(AgentPipelineRun.objects.count(), 1)
        self.assertGreaterEqual(AgentRun.objects.count(), 2)
        self.assertGreaterEqual(AgentHandoff.objects.count(), 1)
        self.assertGreaterEqual(PredictionScore.objects.count(), 1)

    def test_summary_endpoint_returns_pipeline_aggregates(self):
        self._seed_candidate()
        self.client.post(
            reverse('agents:run-pipeline'),
            {'pipeline_type': 'research_to_prediction', 'triggered_from': 'manual', 'payload': {'candidate_limit': 1}},
            format='json',
        )

        response = self.client.get(reverse('agents:summary'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload['total_agents'], 5)
        self.assertGreaterEqual(payload['total_pipeline_runs'], 1)
        self.assertIn('research_to_prediction', payload['pipelines_by_type'])
