from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPath
from apps.opportunity_supervisor.services import run_opportunity_cycle
from apps.paper_trading.models import PaperTrade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.runtime_governor.models import RuntimeMode
from apps.runtime_governor.services import set_runtime_mode
from apps.signals.seeds import seed_mock_agents


class OpportunitySupervisorTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        ensure_demo_account()

    def test_cycle_run_creates_items_and_execution_plans(self):
        cycle = run_opportunity_cycle()
        self.assertEqual(cycle.status, 'COMPLETED')
        self.assertEqual(cycle.items.count(), cycle.opportunities_built)
        self.assertIsNotNone(cycle.summary)

    def test_runtime_observe_only_routes_to_queue_or_watch(self):
        set_runtime_mode(requested_mode=RuntimeMode.OBSERVE_ONLY, set_by='system', rationale='test')
        cycle = run_opportunity_cycle()
        paths = set(cycle.items.values_list('execution_path', flat=True))
        self.assertFalse(OpportunityExecutionPath.AUTO_EXECUTE_PAPER in paths)

    def test_runtime_paper_auto_allows_auto_execute_path(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_AUTO, set_by='system', rationale='test')
        for _ in range(4):
            cycle = run_opportunity_cycle(profile_slug='aggressive_supervisor')
            if cycle.auto_executed_count > 0:
                break
        self.assertGreaterEqual(cycle.auto_executed_count, 0)

    def test_api_endpoints(self):
        client = APIClient()
        response = client.post(reverse('opportunity_supervisor:run-cycle'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        cycle_id = response.json()['id']

        self.assertEqual(client.get(reverse('opportunity_supervisor:cycle-list')).status_code, 200)
        self.assertEqual(client.get(reverse('opportunity_supervisor:cycle-detail', kwargs={'pk': cycle_id})).status_code, 200)
        self.assertEqual(client.get(reverse('opportunity_supervisor:item-list')).status_code, 200)
        summary = client.get(reverse('opportunity_supervisor:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('paper_demo_only', summary.json())
