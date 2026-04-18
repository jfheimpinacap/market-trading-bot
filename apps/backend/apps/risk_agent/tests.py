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
from apps.prediction_agent.services.run import run_prediction_intake_review
from apps.risk_agent.models import AutonomousExecutionReadiness, PositionWatchEvent, RiskApprovalDecision, RiskLevel, RiskRuntimeRun, RiskSizingPlan
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
        run_prediction_intake_review(triggered_by='risk_runtime_tests')

    def test_runtime_run_creates_candidate_approval_sizing_watch(self):
        run = run_risk_runtime_review(triggered_by='test')
        self.assertGreaterEqual(run.considered_handoff_count, 1)
        self.assertGreaterEqual(run.candidate_count, 1)
        self.assertGreaterEqual(RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=run).count(), 1)
        self.assertGreaterEqual(RiskSizingPlan.objects.filter(linked_candidate__runtime_run=run).count(), 1)
        self.assertGreaterEqual(AutonomousExecutionReadiness.objects.filter(linked_approval_review__linked_candidate__runtime_run=run).count(), 1)

    def test_block_for_low_confidence_or_poor_liquidity(self):
        self.market.liquidity = Decimal('500.00')
        self.market.save(update_fields=['liquidity', 'updated_at'])
        run = run_risk_runtime_review(triggered_by='test-poor-liquidity')
        blocked = RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=run, approval_status='BLOCKED').count()
        self.assertGreaterEqual(blocked, 1)

    def test_runtime_api_endpoints_and_summary(self):
        response = self.client.post(reverse('risk_agent:run-intake-review'), {'triggered_by': 'api-test'}, format='json')
        self.assertEqual(response.status_code, 201)
        run_id = response.json()['id']
        self.assertEqual(self.client.get(reverse('risk_agent:intake-candidates'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:approval-reviews'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:execution-readiness'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:intake-recommendations'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:sizing-plans'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(self.client.get(reverse('risk_agent:watch-plans'), {'run_id': run_id}).status_code, 200)
        summary = self.client.get(reverse('risk_agent:intake-summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIsNotNone(summary.json().get('latest_run'))

    def test_readiness_throttle_helper_blocks_only_redundant_additive_with_active_position(self):
        from apps.risk_agent.services.run import _should_throttle_readiness_for_valid_active_exposure

        candidate = type(
            'Candidate',
            (),
            {
                'linked_market_id': 101,
                'context_summary': 'normal additive entry',
                'reason_codes': ['READY_FOR_RISK_RUNTIME'],
            },
        )()
        self.assertFalse(
            _should_throttle_readiness_for_valid_active_exposure(
                candidate=candidate,
                approval_status='APPROVED',
                traced_markets=set(),
                active_position_market_ids={101},
            )
        )
        self.assertTrue(
            _should_throttle_readiness_for_valid_active_exposure(
                candidate=candidate,
                approval_status='APPROVED',
                traced_markets={101},
                active_position_market_ids={101},
            )
        )
        reduce_candidate = type(
            'Candidate',
            (),
            {
                'linked_market_id': 101,
                'context_summary': 'reduce exposure on existing leg',
                'reason_codes': ['REDUCE'],
            },
        )()
        self.assertFalse(
            _should_throttle_readiness_for_valid_active_exposure(
                candidate=reduce_candidate,
                approval_status='APPROVED_REDUCED',
                traced_markets={101},
                active_position_market_ids={101},
            )
        )

    def test_canonical_readiness_throttle_signal_is_persisted_on_approval_decision(self):
        from apps.risk_agent.services.run import _record_canonical_readiness_throttle_signal

        run = run_risk_runtime_review(triggered_by='test-canonical-throttle-signal')
        approval = RiskApprovalDecision.objects.filter(linked_candidate__runtime_run=run).order_by('id').first()
        self.assertIsNotNone(approval)

        _record_canonical_readiness_throttle_signal(
            approval=approval,
            market_id=int(approval.linked_candidate.linked_market_id),
        )
        approval.refresh_from_db()
        signal = dict((approval.metadata or {}).get('readiness_throttle_signal') or {})

        self.assertEqual(signal.get('market_id'), approval.linked_candidate.linked_market_id)
        self.assertEqual(signal.get('risk_decision_id'), approval.id)
        self.assertEqual(signal.get('candidate_shape'), 'additive_entry')
        self.assertEqual(signal.get('throttle_action'), 'skip_redundant_readiness')
        self.assertEqual(signal.get('blocker_validity_status'), 'VALID_ACTIVE_POSITION')
        self.assertEqual(signal.get('release_readiness_status'), 'KEEP_BLOCKED')
        self.assertEqual(signal.get('source_stage'), 'risk_runtime_review')
        self.assertEqual(signal.get('expected_route'), 'execution_intake')
        self.assertTrue(signal.get('readiness_creation_skipped'))
        self.assertIn('READINESS_THROTTLE_CANONICAL_SIGNAL_RECORDED', approval.reason_codes)

    @patch('apps.risk_agent.services.run.build_runtime_recommendations')
    @patch('apps.risk_agent.services.run.build_execution_readiness')
    @patch('apps.risk_agent.services.run.build_watch_plan')
    @patch('apps.risk_agent.services.run.build_sizing_plan')
    @patch('apps.risk_agent.services.run.build_approval_decision')
    @patch('apps.risk_agent.services.run.build_runtime_candidates')
    @patch('apps.risk_agent.services.run.PaperPosition.objects.filter')
    def test_risk_runtime_review_throttles_redundant_same_market_additive_before_readiness(
        self,
        mock_positions_filter,
        mock_build_candidates,
        mock_build_approval,
        mock_build_sizing,
        mock_build_watch,
        mock_build_readiness,
        _mock_recommendations,
    ):
        from types import SimpleNamespace

        from apps.risk_agent.services.intake import IntakeBuildResult

        candidate_initial = SimpleNamespace(linked_market_id=101, context_summary='additive entry', reason_codes=['ENTRY'])
        candidate_redundant = SimpleNamespace(linked_market_id=101, context_summary='additive entry retry', reason_codes=['ENTRY'])
        candidate_exit = SimpleNamespace(linked_market_id=101, context_summary='reduce and exit leg', reason_codes=['EXIT'])
        candidate_without_blocker = SimpleNamespace(linked_market_id=202, context_summary='new additive candidate', reason_codes=['ENTRY'])

        mock_build_candidates.return_value = IntakeBuildResult(
            candidates=[candidate_initial, candidate_redundant, candidate_exit, candidate_without_blocker],
            considered_count=4,
            skipped_count=0,
        )
        mock_positions_filter.return_value.values_list.return_value = [101]

        approval_counter = {'value': 0}

        def _approval_side_effect(*, candidate):
            approval_counter['value'] += 1
            return SimpleNamespace(
                id=approval_counter['value'],
                approval_status='APPROVED_REDUCED' if 'EXIT' in str(candidate.context_summary).upper() else 'APPROVED',
                reason_codes=[],
                metadata={},
                watch_required=False,
                save=lambda **kwargs: None,
            )

        mock_build_approval.side_effect = _approval_side_effect
        mock_build_sizing.return_value = SimpleNamespace()
        mock_build_watch.return_value = SimpleNamespace()
        mock_build_readiness.side_effect = [
            SimpleNamespace(id=1, readiness_status='READY', created_at=None),
            SimpleNamespace(id=2, readiness_status='READY_REDUCED', created_at=None),
            SimpleNamespace(id=3, readiness_status='READY', created_at=None),
        ]

        run = run_risk_runtime_review(triggered_by='test-risk-throttle')
        summary = dict((run.metadata or {}).get('active_exposure_risk_throttle_summary') or {})
        examples = list((run.metadata or {}).get('active_exposure_risk_throttle_examples') or [])

        self.assertEqual(mock_build_approval.call_count, 3)
        self.assertEqual(summary.get('markets_throttled'), 1)
        self.assertEqual(summary.get('redundant_risk_decisions_throttled'), 1)
        self.assertEqual(summary.get('risk_decisions_created_normally'), 3)
        self.assertEqual(summary.get('candidates_preserved_for_exit'), 1)
        self.assertEqual(summary.get('candidates_preserved_without_valid_blocker'), 1)
        self.assertIn('ACTIVE_EXPOSURE_RISK_THROTTLE_SKIPPED_REDUNDANT_DECISION', summary.get('throttle_reason_codes', []))
        self.assertIn('ACTIVE_EXPOSURE_RISK_THROTTLE_ALLOWED_INITIAL_TRACE', summary.get('throttle_reason_codes', []))
        self.assertIn('ACTIVE_EXPOSURE_RISK_THROTTLE_BYPASSED_FOR_EXIT', summary.get('throttle_reason_codes', []))
        self.assertIn(
            'ACTIVE_EXPOSURE_RISK_THROTTLE_BYPASSED_WITHOUT_VALID_BLOCKER',
            summary.get('throttle_reason_codes', []),
        )
        self.assertTrue(any(example.get('risk_decision_creation_skipped') for example in examples))
