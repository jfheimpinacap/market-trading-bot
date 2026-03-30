from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.agents.services.orchestrator import run_agent_pipeline
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.memory_retrieval.models import MemoryDocument
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.prediction_agent.services.run import run_prediction_runtime_review
from apps.risk_agent.models import PositionWatchEvent, RiskApprovalDecision, RiskLevel, RiskRuntimeRun, RiskSizingPlan
from apps.risk_agent.services import run_position_watch, run_risk_assessment, run_risk_runtime_review, run_risk_sizing


class RiskAgentServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.filter(is_active=True).order_by('id').first()
        self.prediction = score_market_prediction(market=self.market, triggered_by='risk_agent_tests').score
        MemoryDocument.objects.create(
            document_type='risk_assessment_snapshot',
            source_app='risk_agent',
            source_object_id='risk-1',
            title='Adverse risk precedent',
            text_content='similar risk setup ended in loss and review escalation',
            tags=['negative', 'failed'],
            structured_summary={'primary_failure_mode': 'oversizing_under_pressure'},
            embedding=[1.0, 0.0, 0.0],
            embedding_model='mock',
        )

    @patch('apps.memory_retrieval.services.retrieval.embed_text', return_value=[1.0, 0.0, 0.0])
    def test_assessment_and_sizing_basic(self, _retrieval_embed):
        assessment = run_risk_assessment(market=self.market, prediction_score=self.prediction)
        self.assertIn(assessment.risk_level, {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.BLOCKED})
        self.assertIn('precedent_context', assessment.metadata)
        sizing = run_risk_sizing(risk_assessment=assessment, base_quantity=Decimal('10.0000'))
        self.assertGreaterEqual(sizing.adjusted_quantity, Decimal('0.0000'))

    def test_blocked_assessment_produces_zero_quantity(self):
        self.market.is_active = False
        self.market.save(update_fields=['is_active', 'updated_at'])
        assessment = run_risk_assessment(market=self.market, prediction_score=self.prediction)
        self.assertEqual(assessment.risk_level, RiskLevel.BLOCKED)
        sizing = run_risk_sizing(risk_assessment=assessment, base_quantity=Decimal('10.0000'))
        self.assertEqual(sizing.adjusted_quantity, Decimal('0.0000'))

    def test_watch_detects_deterioration(self):
        execute_paper_trade(market=self.market, trade_type='BUY', side='YES', quantity=Decimal('5.0000'), account=self.account)
        position = self.account.positions.get(market=self.market, side='YES')
        position.unrealized_pnl = Decimal('-200.00')
        position.save(update_fields=['unrealized_pnl', 'updated_at'])
        run = run_position_watch()
        self.assertEqual(run.watched_positions, 1)
        self.assertGreaterEqual(PositionWatchEvent.objects.count(), 1)


class RiskAgentApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.filter(is_active=True).order_by('id').first()
        self.prediction = score_market_prediction(market=self.market, triggered_by='risk_agent_tests').score

    def test_endpoints(self):
        assess = self.client.post(reverse('risk_agent:assess'), {'market_id': self.market.id, 'prediction_score_id': self.prediction.id}, format='json')
        self.assertEqual(assess.status_code, 201)
        assessment_id = assess.json()['assessment']['id']
        size = self.client.post(reverse('risk_agent:size'), {'risk_assessment_id': assessment_id, 'base_quantity': '8.0000'}, format='json')
        self.assertEqual(size.status_code, 201)
        watch = self.client.post(reverse('risk_agent:run-watch'), {}, format='json')
        self.assertEqual(watch.status_code, 201)
        self.assertEqual(self.client.get(reverse('risk_agent:assessments')).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:watch-events')).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:summary')).status_code, 200)

    def test_agents_pipeline_integration(self):
        run = run_agent_pipeline(pipeline_type='real_market_agent_cycle', payload={'market_limit': 1, 'quantity': '2.0000'})
        self.assertIn(run.status, ['SUCCESS', 'PARTIAL'])


class RiskRuntimeHardeningTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.filter(is_active=True).order_by('id').first()
        score_market_prediction(market=self.market, triggered_by='risk_runtime_tests')
        run_prediction_runtime_review(triggered_by='risk_runtime_tests')

    def test_runtime_run_creates_candidate_approval_sizing_watch(self):
        run = run_risk_runtime_review(triggered_by='test')
        self.assertGreaterEqual(run.candidate_count, 1)
        self.assertGreaterEqual(RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=run).count(), 1)
        self.assertGreaterEqual(RiskSizingPlan.objects.filter(linked_candidate__runtime_run=run).count(), 1)

    def test_block_for_low_confidence_or_poor_liquidity(self):
        self.market.liquidity = Decimal('500.00')
        self.market.save(update_fields=['liquidity', 'updated_at'])
        run = run_risk_runtime_review(triggered_by='test-poor-liquidity')
        blocked = RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=run, approval_status='BLOCKED').count()
        self.assertGreaterEqual(blocked, 1)

    def test_runtime_api_endpoints_and_summary(self):
        response = self.client.post(reverse('risk_agent:run-runtime-review'), {'triggered_by': 'api-test'}, format='json')
        self.assertEqual(response.status_code, 201)
        run_id = response.json()['id']
        self.assertEqual(self.client.get(reverse('risk_agent:runtime-candidates'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:approval-decisions'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:sizing-plans'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:watch-plans'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:runtime-recommendations'), {'run_id': run_id}).status_code, 200)
        summary = self.client.get(reverse('risk_agent:runtime-summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIsNotNone(summary.json().get('latest_run'))
