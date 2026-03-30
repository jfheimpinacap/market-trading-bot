from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.continuous_demo.models import ContinuousDemoSession, SessionStatus
from apps.evaluation_lab.models import EvaluationRuntimeRun
from apps.evaluation_lab.services import build_run_for_continuous_session
from apps.evaluation_lab.services.run import run_runtime_evaluation
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market, MarketStatus
from apps.opportunity_supervisor.models import (
    OpportunityCycleRuntimeRun,
    OpportunityFusionAssessment,
    OpportunityFusionCandidate,
    PaperOpportunityProposal,
)
from apps.paper_trading.models import PaperPortfolioSnapshot
from apps.paper_trading.services.execution import execute_paper_trade
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome, TradeReviewStatus
from apps.prediction_agent.models import PredictionRuntimeAssessment, PredictionRuntimeCandidate, PredictionRuntimeRun
from apps.risk_agent.models import RiskApprovalDecision, RiskRuntimeCandidate, RiskRuntimeRun
from apps.safety_guard.models import SafetyEvent, SafetyEventSource, SafetyEventType, SafetySeverity


class EvaluationLabTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.order_by('id').first()
        self.client = APIClient()

    def _build_session_with_data(self):
        session = ContinuousDemoSession.objects.create(session_status=SessionStatus.STOPPED)
        session.started_at = session.created_at
        session.finished_at = session.created_at
        session.save(update_fields=['started_at', 'finished_at'])

        trade = execute_paper_trade(
            market=self.market,
            trade_type='BUY',
            side='YES',
            quantity=Decimal('1.0000'),
            account=self.account,
        )
        TradeReview.objects.create(
            paper_trade=trade,
            paper_account=self.account,
            market=self.market,
            review_status=TradeReviewStatus.REVIEWED,
            outcome=TradeReviewOutcome.FAVORABLE,
            score=Decimal('70.00'),
            confidence=Decimal('0.70'),
            summary='Good trade',
        )
        PaperPortfolioSnapshot.objects.create(
            account=self.account,
            cash_balance=self.account.cash_balance,
            equity=Decimal('10010.00'),
            realized_pnl=Decimal('10.00'),
            unrealized_pnl=Decimal('0.00'),
            total_pnl=Decimal('10.00'),
            open_positions_count=1,
        )
        SafetyEvent.objects.create(
            event_type=SafetyEventType.WARNING,
            severity=SafetySeverity.WARNING,
            source=SafetyEventSource.CONTINUOUS_DEMO,
            message='Test warning',
        )
        return session

    def _seed_runtime_links(self):
        market = Market.objects.filter(status=MarketStatus.RESOLVED).first() or self.market
        market.status = MarketStatus.RESOLVED
        market.metadata = {**(market.metadata or {}), 'resolved_outcome': 'yes'}
        market.save(update_fields=['status', 'metadata'])

        prediction_run = PredictionRuntimeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        prediction_candidate = PredictionRuntimeCandidate.objects.create(runtime_run=prediction_run, linked_market=market, market_provider=market.provider.slug, category=market.category)
        prediction_assessment = PredictionRuntimeAssessment.objects.create(
            linked_candidate=prediction_candidate,
            active_model_name='demo-model',
            model_mode='blended',
            system_probability=Decimal('0.6800'),
            calibrated_probability=Decimal('0.7200'),
            market_probability=Decimal('0.5200'),
            raw_edge=Decimal('0.1600'),
            adjusted_edge=Decimal('0.1400'),
            confidence_score=Decimal('0.7600'),
            uncertainty_score=Decimal('0.2200'),
            evidence_quality_score=Decimal('0.7000'),
            precedent_caution_score=Decimal('0.1000'),
            narrative_influence_score=Decimal('0.6000'),
            prediction_status='STRONG_EDGE',
        )

        risk_run = RiskRuntimeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        risk_candidate = RiskRuntimeCandidate.objects.create(
            runtime_run=risk_run,
            linked_prediction_assessment=prediction_assessment,
            linked_market=market,
            market_provider=market.provider.slug,
            category=market.category,
            calibrated_probability=Decimal('0.7200'),
            adjusted_edge=Decimal('0.1400'),
            confidence_score=Decimal('0.7600'),
            uncertainty_score=Decimal('0.2200'),
            evidence_quality_score=Decimal('0.7000'),
            precedent_caution_score=Decimal('0.1000'),
        )
        risk_approval = RiskApprovalDecision.objects.create(linked_candidate=risk_candidate, approval_status='APPROVED', risk_score=Decimal('0.2000'))

        cycle_run = OpportunityCycleRuntimeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        fusion_candidate = OpportunityFusionCandidate.objects.create(runtime_run=cycle_run, linked_market=market, linked_prediction_assessment=prediction_assessment, linked_risk_approval=risk_approval, provider=market.provider.slug, category=market.category, adjusted_edge=Decimal('0.1400'))
        fusion_assessment = OpportunityFusionAssessment.objects.create(runtime_run=cycle_run, linked_candidate=fusion_candidate, fusion_status='READY_FOR_PROPOSAL', conviction_score=Decimal('0.8000'))
        PaperOpportunityProposal.objects.create(runtime_run=cycle_run, linked_assessment=fusion_assessment, proposal_status='READY', calibrated_probability=Decimal('0.7200'), adjusted_edge=Decimal('0.1400'))

    def test_build_metrics_for_session(self):
        session = self._build_session_with_data()
        run = build_run_for_continuous_session(session)

        self.assertEqual(run.status, 'READY')
        self.assertIsNotNone(run.metric_set)
        self.assertGreaterEqual(run.metric_set.trades_executed_count, 1)
        self.assertEqual(run.metric_set.favorable_reviews_count, 1)

    def test_runtime_evaluation_builds_alignment_and_summary(self):
        self._seed_runtime_links()
        runtime_run = run_runtime_evaluation()

        self.assertIsInstance(runtime_run, EvaluationRuntimeRun)
        self.assertGreaterEqual(runtime_run.resolved_market_count, 1)
        self.assertGreaterEqual(runtime_run.linked_prediction_count, 1)
        self.assertGreaterEqual(runtime_run.metric_count, 3)
        self.assertGreaterEqual(runtime_run.calibration_bucket_count, 1)

        summary_response = self.client.get(reverse('evaluation_lab:runtime-summary'))
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertIsNotNone(summary['latest_run'])

    def test_runtime_api_endpoints(self):
        self._seed_runtime_links()
        run_response = self.client.post(reverse('evaluation_lab:run-runtime-evaluation'), data={}, content_type='application/json')
        self.assertEqual(run_response.status_code, 201)

        alignment = self.client.get(reverse('evaluation_lab:outcome-alignment'))
        buckets = self.client.get(reverse('evaluation_lab:calibration-buckets'))
        metrics = self.client.get(reverse('evaluation_lab:effectiveness-metrics'))
        recommendations = self.client.get(reverse('evaluation_lab:recommendations'))

        self.assertEqual(alignment.status_code, 200)
        self.assertEqual(buckets.status_code, 200)
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(recommendations.status_code, 200)
        self.assertGreaterEqual(len(alignment.json()), 1)
        self.assertGreaterEqual(len(buckets.json()), 1)
        self.assertGreaterEqual(len(metrics.json()), 1)
