from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.autonomous_trader.models import AutonomousTradeCycleRun, AutonomousTradeDecision
from apps.autonomous_trader.services.candidate_intake import consolidate_candidates
from apps.autonomous_trader.services.decisioning import decide_candidate
from apps.autonomous_trader.services.execution import execute_candidate
from apps.autonomous_trader.services.outcomes import create_outcome
from apps.autonomous_trader.services.watch import create_watch_record
from apps.markets.models import Event, Market, MarketStatus, Provider
from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun, OpportunityFusionCandidate
from apps.paper_trading.services.portfolio import ensure_demo_account


class AutonomousTraderFlowTests(TestCase):
    def setUp(self):
        ensure_demo_account()
        self.client = APIClient()
        provider = Provider.objects.create(name='Demo Provider', slug='demo-provider')
        event = Event.objects.create(provider=provider, title='Election', slug='election-2026')
        self.market = Market.objects.create(
            provider=provider,
            event=event,
            title='Will candidate X win?',
            slug='candidate-x-win',
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('0.40'),
            current_no_price=Decimal('0.60'),
            volume_total=Decimal('100000.00'),
            liquidity=Decimal('50000.00'),
            close_time=timezone.now() + timezone.timedelta(days=20),
        )
        runtime_run = OpportunityCycleRuntimeRun.objects.create(started_at=timezone.now())
        OpportunityFusionCandidate.objects.create(
            runtime_run=runtime_run,
            linked_market=self.market,
            adjusted_edge=Decimal('0.1200'),
            confidence_score=Decimal('0.8000'),
            market_probability=Decimal('0.4000'),
            metadata={},
        )

    def test_candidate_intake_and_decision(self):
        cycle = AutonomousTradeCycleRun.objects.create()
        intake = consolidate_candidates(cycle_run=cycle)
        self.assertGreaterEqual(len(intake.candidates), 1)
        decision = decide_candidate(candidate=intake.candidates[0])
        self.assertTrue(decision.decision_type)

    def test_execution_watch_outcome_and_summary_endpoint(self):
        run_response = self.client.post('/api/autonomous-trader/run-cycle/', {'actor': 'test-suite'}, format='json')
        self.assertEqual(run_response.status_code, 200)

        decisions = AutonomousTradeDecision.objects.order_by('-id')
        self.assertTrue(decisions.exists())
        execution = execute_candidate(decision=decisions.first())
        watch = create_watch_record(execution=execution)
        outcome = create_outcome(execution=execution, watch_record=watch)
        self.assertIsNotNone(outcome.id)

        summary_response = self.client.get('/api/autonomous-trader/summary/')
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('latest_run_id', summary_response.json())
