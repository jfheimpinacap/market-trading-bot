from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.allocation_engine.models import AllocationDecision, AllocationDecisionType, AllocationRun
from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_simulator.models import PaperFill, PaperOrder
from apps.execution_venue.models import VenueOrderPayload, VenueOrderResponse, VenueResponseStatus
from apps.incident_commander.models import DegradedModeState, IncidentRecord, IncidentSeverity, IncidentStatus
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.memory_retrieval.models import AgentPrecedentUse, MemoryQueryType, MemoryRetrievalRun, PrecedentInfluenceMode
from apps.opportunity_supervisor.models import OpportunityCycleItem, OpportunityCycleRun, OpportunityExecutionPath
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.prediction_agent.models import PredictionConfidenceLevel, PredictionModelProfile, PredictionRun, PredictionScore, PredictionRunStatus
from apps.proposal_engine.models import ProposalDirection, ProposalStatus, ProposalTradeType, TradeProposal
from apps.research_agent.models import NarrativeSentiment, ResearchCandidate
from apps.risk_agent.models import RiskAssessment, RiskAssessmentStatus, RiskLevel
from apps.signals.models import OpportunitySignal, OpportunityStatus, SignalRunStatus, SignalFusionRun
from apps.trace_explorer.models import TraceQueryRun


class TraceExplorerTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account = ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')

        self.research = ResearchCandidate.objects.create(market=self.market, sentiment_direction=NarrativeSentiment.BULLISH, short_thesis='Research suggests momentum.', priority=Decimal('90.0'))
        profile = PredictionModelProfile.objects.create(slug='test-profile', name='Test profile')
        run = PredictionRun.objects.create(status=PredictionRunStatus.SUCCESS, triggered_by='test', model_profile=profile, started_at=self.research.created_at)
        self.prediction = PredictionScore.objects.create(run=run, market=self.market, model_profile=profile, market_probability=Decimal('0.42'), system_probability=Decimal('0.57'), edge=Decimal('0.15'), confidence=Decimal('0.80'), confidence_level=PredictionConfidenceLevel.HIGH, model_profile_used='test-profile')
        self.proposal = TradeProposal.objects.create(market=self.market, paper_account=self.account, proposal_status=ProposalStatus.ACTIVE, direction=ProposalDirection.BUY_YES, proposal_score=Decimal('84.0'), confidence=Decimal('0.82'), headline='Test proposal', thesis='Go long yes', suggested_trade_type=ProposalTradeType.BUY, suggested_side='YES', suggested_quantity=Decimal('2.5000'), risk_decision='ALLOW', policy_decision='AUTO_APPROVED', is_actionable=True)
        self.risk = RiskAssessment.objects.create(market=self.market, proposal=self.proposal, prediction_score=self.prediction, assessment_status=RiskAssessmentStatus.SUCCESS, risk_level=RiskLevel.LOW, narrative_risk_summary='Contained risk profile.')

        signal_run = SignalFusionRun.objects.create(status=SignalRunStatus.COMPLETED)
        self.signal = OpportunitySignal.objects.create(run=signal_run, market=self.market, opportunity_status=OpportunityStatus.PROPOSAL_READY, opportunity_score=Decimal('88.0'), rationale='Edge plus confidence')
        cycle_run = OpportunityCycleRun.objects.create(status='COMPLETED')
        self.opportunity = OpportunityCycleItem.objects.create(run=cycle_run, market=self.market, proposal=self.proposal, execution_path=OpportunityExecutionPath.AUTO_EXECUTE_PAPER, rationale='Approved for paper execution')

        allocation_run = AllocationRun.objects.create(status='SUCCESS')
        self.allocation = AllocationDecision.objects.create(run=allocation_run, proposal=self.proposal, decision=AllocationDecisionType.SELECTED, final_allocated_quantity=Decimal('2.0000'))

        self.paper_order = PaperOrder.objects.create(paper_account=self.account, market=self.market, side='BUY_YES', requested_quantity=Decimal('2.0000'), remaining_quantity=Decimal('0.0000'), status='FILLED', created_from='manual')
        self.fill = PaperFill.objects.create(paper_order=self.paper_order, fill_quantity=Decimal('2.0000'), fill_price=Decimal('0.53'), fill_type='full')
        self.intent = BrokerOrderIntent.objects.create(related_paper_order=self.paper_order, market=self.market, source_type='paper_order', source_id=str(self.paper_order.id), source_ref=f'paper_order:{self.paper_order.id}', side='BUY_YES', quantity=Decimal('2.0000'))
        self.venue_payload = VenueOrderPayload.objects.create(intent=self.intent, venue_name='sandbox_venue', side='buy', order_type='market_like', quantity=Decimal('2.0000'), source_intent_id=self.intent.id)
        self.venue_response = VenueOrderResponse.objects.create(intent=self.intent, payload=self.venue_payload, normalized_status=VenueResponseStatus.ACCEPTED, external_order_id='ext-1')

        self.retrieval_run = MemoryRetrievalRun.objects.create(query_text='precedent query', query_type=MemoryQueryType.RISK, result_count=2)
        self.precedent = AgentPrecedentUse.objects.create(agent_name='risk_agent', source_app='proposal_engine', source_object_id=str(self.proposal.id), retrieval_run=self.retrieval_run, precedent_count=2, influence_mode=PrecedentInfluenceMode.CAUTION_BOOST)

        self.incident = IncidentRecord.objects.create(incident_type='execution_anomaly', severity=IncidentSeverity.HIGH, status=IncidentStatus.DEGRADED, title='Execution delay', summary='Simulator delay observed', source_app='execution_simulator', related_object_type='paper_order', related_object_id=str(self.paper_order.id), first_seen_at=self.paper_order.created_at, last_seen_at=self.paper_order.created_at)
        self.degraded = DegradedModeState.objects.create(state='execution_degraded', mission_control_paused=True, auto_execution_enabled=False, reasons=['incident_open'])

    def test_build_trace_for_opportunity_includes_precedent_execution_and_incident(self):
        response = self.client.post(reverse('trace_explorer:query'), {'root_type': 'opportunity', 'root_id': str(self.opportunity.id)}, format='json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        node_types = {node['node_type'] for node in payload['nodes']}
        self.assertIn('AgentPrecedentUse', node_types)
        self.assertIn('PaperOrder', node_types)
        self.assertIn('BrokerOrderIntent', node_types)
        self.assertIn('VenueOrderPayload', node_types)
        self.assertIn('IncidentRecord', node_types)

    def test_snapshot_and_summary_endpoints(self):
        self.client.post(reverse('trace_explorer:query'), {'root_type': 'opportunity', 'root_id': str(self.opportunity.id)}, format='json')
        snapshot = self.client.get(reverse('trace_explorer:snapshot', kwargs={'root_type': 'opportunity', 'root_id': str(self.opportunity.id)}))
        runs = self.client.get(reverse('trace_explorer:query-runs'))
        summary = self.client.get(reverse('trace_explorer:summary'))
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(summary.status_code, 200)
        self.assertGreaterEqual(TraceQueryRun.objects.count(), 1)
