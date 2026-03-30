from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.learning_memory.models import LoopAdjustmentStatus, LoopAdjustmentType, PostmortemLearningAdjustment
from apps.markets.demo_data import seed_demo_markets
from apps.opportunity_supervisor.models import OpportunityFusionStatus
from apps.opportunity_supervisor.services.candidate_building import build_fusion_candidates
from apps.opportunity_supervisor.services.run import run_opportunity_cycle_review
from apps.prediction_agent.models import (
    PredictionAssessmentStatus,
    PredictionRuntimeAssessment,
    PredictionRuntimeCandidate,
    PredictionRuntimeModelMode,
    PredictionRuntimeRun,
)
from apps.research_agent.models import MarketResearchCandidate, MarketResearchCandidateStatus, MarketUniverseRun
from apps.risk_agent.models import (
    PositionWatchPlan,
    PositionWatchPlanStatus,
    RiskApprovalDecision,
    RiskRuntimeApprovalStatus,
    RiskRuntimeCandidate,
    RiskRuntimeRun,
    RiskRuntimeSizingMode,
    RiskSizingPlan,
)


class OpportunityCycleRuntimeTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.market = self._build_market()
        self.research = self._build_research_candidate()
        self.prediction_assessment = self._build_prediction_assessment()
        self.approval = self._build_risk_records()

    def _build_market(self):
        from apps.markets.models import Market

        return Market.objects.order_by('id').first()

    def _build_research_candidate(self):
        universe = MarketUniverseRun.objects.create(started_at=timezone.now())
        return MarketResearchCandidate.objects.create(
            universe_run=universe,
            linked_market=self.market,
            market_title=self.market.title,
            market_provider=self.market.provider.slug if self.market.provider_id else 'demo',
            category='politics',
            narrative_support_score=Decimal('0.8100'),
            pursue_worthiness_score=Decimal('0.7600'),
            status=MarketResearchCandidateStatus.SHORTLIST,
            linked_narrative_signals=[{'signal_id': 'n1'}],
        )

    def _build_prediction_assessment(self):
        prediction_run = PredictionRuntimeRun.objects.create(started_at=timezone.now())
        prediction_candidate = PredictionRuntimeCandidate.objects.create(
            runtime_run=prediction_run,
            linked_market=self.market,
            linked_research_candidate=self.research,
            linked_scan_signals=[{'signal_id': 'n1'}],
            market_provider='demo',
            category='politics',
            market_probability=Decimal('0.5400'),
            narrative_support_score=Decimal('0.8100'),
            divergence_score=Decimal('0.1200'),
            research_status='SHORTLIST',
            candidate_quality_score=Decimal('0.7900'),
        )
        return PredictionRuntimeAssessment.objects.create(
            linked_candidate=prediction_candidate,
            active_model_name='heuristic',
            model_mode=PredictionRuntimeModelMode.HEURISTIC_ONLY,
            system_probability=Decimal('0.6200'),
            calibrated_probability=Decimal('0.6100'),
            market_probability=Decimal('0.5400'),
            raw_edge=Decimal('0.0800'),
            adjusted_edge=Decimal('0.0700'),
            confidence_score=Decimal('0.7300'),
            uncertainty_score=Decimal('0.2700'),
            evidence_quality_score=Decimal('0.6800'),
            precedent_caution_score=Decimal('0.1200'),
            narrative_influence_score=Decimal('0.5000'),
            prediction_status=PredictionAssessmentStatus.STRONG_EDGE,
        )

    def _build_risk_records(self):
        risk_run = RiskRuntimeRun.objects.create(started_at=timezone.now())
        risk_candidate = RiskRuntimeCandidate.objects.create(
            runtime_run=risk_run,
            linked_prediction_assessment=self.prediction_assessment,
            linked_market=self.market,
            market_provider='demo',
            category='politics',
            calibrated_probability=Decimal('0.6100'),
            adjusted_edge=Decimal('0.0700'),
            confidence_score=Decimal('0.7300'),
            uncertainty_score=Decimal('0.2700'),
            evidence_quality_score=Decimal('0.6800'),
            precedent_caution_score=Decimal('0.1200'),
        )
        approval = RiskApprovalDecision.objects.create(
            linked_candidate=risk_candidate,
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
            risk_score=Decimal('0.7400'),
            watch_required=False,
        )
        sizing = RiskSizingPlan.objects.create(
            linked_candidate=risk_candidate,
            linked_approval_decision=approval,
            sizing_mode=RiskRuntimeSizingMode.FIXED_FRACTION,
            raw_size_fraction=Decimal('0.060000'),
            adjusted_size_fraction=Decimal('0.040000'),
            paper_notional_size=Decimal('150.00'),
        )
        PositionWatchPlan.objects.create(
            linked_candidate=risk_candidate,
            linked_sizing_plan=sizing,
            watch_status=PositionWatchPlanStatus.OPTIONAL,
        )
        return approval

    def test_candidate_building_from_research_prediction_risk(self):
        from apps.opportunity_supervisor.models import OpportunityCycleRuntimeRun

        run = OpportunityCycleRuntimeRun.objects.create(started_at=timezone.now())
        candidates = build_fusion_candidates(runtime_run=run)
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.linked_market_id, self.market.id)
        self.assertEqual(candidate.linked_research_candidate_id, self.research.id)
        self.assertEqual(candidate.linked_prediction_assessment_id, self.prediction_assessment.id)
        self.assertEqual(candidate.linked_risk_approval_id, self.approval.id)

    def test_blocking_by_learning_and_risk(self):
        self.approval.approval_status = RiskRuntimeApprovalStatus.BLOCKED
        self.approval.save(update_fields=['approval_status', 'updated_at'])
        run = run_opportunity_cycle_review(triggered_by='test')
        assessment = run.assessments.first()
        self.assertEqual(assessment.fusion_status, OpportunityFusionStatus.BLOCKED_BY_RISK)

        PostmortemLearningAdjustment.objects.create(
            adjustment_type=LoopAdjustmentType.CATEGORY_CAUTION,
            scope='global',
            scope_key='global',
            adjustment_strength=Decimal('0.6000'),
            status=LoopAdjustmentStatus.ACTIVE,
            expiration_hint=timezone.now() + timedelta(days=3),
        )
        self.approval.approval_status = RiskRuntimeApprovalStatus.APPROVED
        self.approval.save(update_fields=['approval_status', 'updated_at'])

        run_learning = run_opportunity_cycle_review(triggered_by='test')
        assessment_learning = run_learning.assessments.first()
        self.assertEqual(assessment_learning.fusion_status, OpportunityFusionStatus.BLOCKED_BY_LEARNING)

    def test_api_endpoints_summary_and_recommendations(self):
        client = APIClient()
        review = client.post(reverse('opportunity_cycle:run-review'), {}, format='json')
        self.assertEqual(review.status_code, 200)
        run_id = review.json()['id']

        self.assertEqual(client.get(reverse('opportunity_cycle:candidate-list'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(client.get(reverse('opportunity_cycle:assessment-list'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(client.get(reverse('opportunity_cycle:proposal-list'), {'run_id': run_id}).status_code, 200)
        self.assertEqual(client.get(reverse('opportunity_cycle:recommendation-list'), {'run_id': run_id}).status_code, 200)
        summary = client.get(reverse('opportunity_cycle:cycle-runtime-summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('candidate_count', summary.json())
