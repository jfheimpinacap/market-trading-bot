from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.prediction_agent.models import PredictionModelProfile, PredictionRun, PredictionScore
from apps.research_agent.models import MarketTriageDecision, MarketUniverseScanRun, PursuitCandidate, TriageStatus
from apps.risk_agent.models import RiskAssessment, RiskLevel, RiskSizingDecision
from apps.runtime_governor.models import RuntimeMode, RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyPolicyConfig, SafetyStatus
from apps.signals.models import MarketSignal, MockAgent, OpportunitySignal, OpportunityStatus, ProposalGateDecision, SignalFusionRun, SignalRun
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals, run_signal_fusion


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


class SignalFusionTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        self.market = Market.objects.order_by('id').first()
        self._seed_research_prediction_risk_inputs()

    def _seed_research_prediction_risk_inputs(self):
        run = MarketUniverseScanRun.objects.create(
            status='success',
            triggered_by='test',
            started_at=timezone.now() - timedelta(minutes=5),
            finished_at=timezone.now(),
        )
        triage = MarketTriageDecision.objects.create(
            run=run,
            market=self.market,
            triage_status=TriageStatus.SHORTLISTED,
            triage_score=Decimal('74.00'),
            narrative_coverage=6,
            narrative_relevance=Decimal('0.7400'),
            narrative_confidence=Decimal('0.7600'),
            source_mix='mixed',
            rationale='Test shortlist candidate',
            details={'narrative_confidence': '0.7600'},
        )
        PursuitCandidate.objects.create(
            run=run,
            triage_decision=triage,
            market=self.market,
            provider_slug=self.market.provider.slug,
            market_probability=Decimal('0.5400'),
            narrative_coverage=6,
            narrative_direction='bullish',
            source_mix='mixed',
            triage_score=Decimal('74.00'),
            triage_status=TriageStatus.SHORTLISTED,
            details={'narrative_confidence': '0.7600'},
        )

        profile = PredictionModelProfile.objects.create(slug='test-profile', name='Test profile')
        prediction_run = PredictionRun.objects.create(
            status='success',
            triggered_by='test',
            model_profile=profile,
            started_at=timezone.now() - timedelta(minutes=3),
            finished_at=timezone.now() - timedelta(minutes=2),
            markets_scored=1,
        )
        score = PredictionScore.objects.create(
            run=prediction_run,
            market=self.market,
            model_profile=profile,
            market_probability=Decimal('0.5400'),
            system_probability=Decimal('0.6200'),
            edge=Decimal('0.0800'),
            confidence=Decimal('0.7000'),
            confidence_level='HIGH',
            edge_label='strong',
            model_profile_used='test-profile',
        )

        assessment = RiskAssessment.objects.create(
            market=self.market,
            prediction_score=score,
            assessment_status='SUCCESS',
            risk_level=RiskLevel.LOW,
            risk_score=Decimal('22.00'),
            safety_context={'paper_demo_only': True},
        )
        RiskSizingDecision.objects.create(
            risk_assessment=assessment,
            base_quantity=Decimal('5.0000'),
            adjusted_quantity=Decimal('3.5000'),
            sizing_mode='heuristic',
        )

        RuntimeModeState.objects.create(
            current_mode=RuntimeMode.PAPER_ASSIST,
            status=RuntimeStateStatus.ACTIVE,
            set_by='manual',
            rationale='test runtime mode',
        )
        SafetyPolicyConfig.objects.create(name='default', status=SafetyStatus.HEALTHY)

    def test_run_signal_fusion_creates_opportunity_and_gate(self):
        run = run_signal_fusion(profile_slug='balanced_signal')

        self.assertEqual(run.status, 'COMPLETED')
        self.assertEqual(run.markets_evaluated, 1)
        opportunity = OpportunitySignal.objects.get(run=run)
        self.assertEqual(opportunity.market_id, self.market.id)
        self.assertGreater(opportunity.opportunity_score, Decimal('0.00'))
        self.assertIn(opportunity.opportunity_status, {OpportunityStatus.CANDIDATE, OpportunityStatus.PROPOSAL_READY, OpportunityStatus.WATCH})

        gate = ProposalGateDecision.objects.get(opportunity=opportunity)
        self.assertIsNotNone(gate.proposal_reason)

    def test_signal_fusion_api_endpoints(self):
        run_response = self.client.post(reverse('signals:signal-run-fusion'), {'profile_slug': 'balanced_signal'}, format='json')
        self.assertEqual(run_response.status_code, 201)
        run_id = run_response.json()['id']

        runs_response = self.client.get(reverse('signals:signal-fusion-run-list'))
        self.assertEqual(runs_response.status_code, 200)
        self.assertGreaterEqual(len(runs_response.json()), 1)

        detail_response = self.client.get(reverse('signals:signal-fusion-run-detail', kwargs={'pk': run_id}))
        self.assertEqual(detail_response.status_code, 200)

        opportunities_response = self.client.get(reverse('signals:signal-opportunities'))
        self.assertEqual(opportunities_response.status_code, 200)
        self.assertGreaterEqual(len(opportunities_response.json()), 1)

        summary_response = self.client.get(reverse('signals:signal-board-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('proposal_ready_count', summary_response.json())

    def test_status_blocked_when_safety_is_hard_stop(self):
        SafetyPolicyConfig.objects.update(status=SafetyStatus.HARD_STOP)
        run = run_signal_fusion(profile_slug='balanced_signal')
        opportunity = OpportunitySignal.objects.get(run=run)

        self.assertEqual(opportunity.opportunity_status, OpportunityStatus.BLOCKED)
        gate = ProposalGateDecision.objects.get(opportunity=opportunity)
        self.assertFalse(gate.should_generate_proposal)
