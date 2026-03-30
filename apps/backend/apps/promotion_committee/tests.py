from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EffectivenessMetric, EffectivenessMetricStatus, EffectivenessMetricType, EvaluationRuntimeRun
from apps.experiment_lab.models import (
    ExperimentCandidate,
    ExperimentCandidateReadinessStatus,
    ExperimentPromotionRecommendation,
    ExperimentPromotionRecommendationType,
    TuningChampionChallengerComparison,
    TuningExperimentRun,
)
from apps.promotion_committee.models import (
    PromotionCase,
    PromotionCaseStatus,
    PromotionDecisionRecommendation,
    PromotionDecisionRecommendationType,
)
from apps.tuning_board.models import (
    TuningComponent,
    TuningPriorityLevel,
    TuningProposal,
    TuningProposalStatus,
    TuningProposalType,
    TuningReviewRun,
    TuningScope,
)


class PromotionCommitteeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _create_candidate_bundle(self, *, sample_count: int, comparison_status: str, confidence: Decimal, scope: str = 'provider'):
        eval_runtime = EvaluationRuntimeRun.objects.create(metric_count=1, recommendation_summary={}, metadata={})
        metric = EffectivenessMetric.objects.create(
            run=eval_runtime,
            metric_type=EffectivenessMetricType.CALIBRATION_ERROR,
            metric_scope='global',
            metric_value=Decimal('0.08'),
            sample_count=sample_count,
            status=EffectivenessMetricStatus.POOR,
            metadata={'baseline_value': '0.10'},
        )
        tuning_run = TuningReviewRun.objects.create(metadata={'source': 'test'})
        proposal = TuningProposal.objects.create(
            run=tuning_run,
            source_metric=metric,
            proposal_type=TuningProposalType.CALIBRATION_BIAS_OFFSET,
            target_scope=TuningScope.GLOBAL,
            target_component=TuningComponent.CALIBRATION,
            proposal_status=TuningProposalStatus.READY_FOR_REVIEW,
            evidence_strength_score=Decimal('0.84'),
            priority_level=TuningPriorityLevel.HIGH,
            rationale='Calibration adjustment for candidate.',
        )
        exp_run = TuningExperimentRun.objects.create(candidate_count=1, comparison_count=1)
        candidate = ExperimentCandidate.objects.create(
            run=exp_run,
            linked_tuning_proposal=proposal,
            candidate_type='calibration_variant',
            challenger_label=f'challenger-{sample_count}-{comparison_status.lower()}',
            experiment_scope=scope,
            readiness_status=ExperimentCandidateReadinessStatus.READY,
            rationale='Experiment candidate rationale.',
            blockers=[],
            metadata={},
        )
        comparison = TuningChampionChallengerComparison.objects.create(
            run=exp_run,
            linked_candidate=candidate,
            baseline_label='baseline',
            challenger_label='challenger',
            comparison_status=comparison_status,
            compared_metrics={'baseline_value': '0.10', 'challenger_value': '0.07'},
            sample_count=sample_count,
            confidence_score=confidence,
            rationale='Comparison rationale',
            reason_codes=['comparison_generated'],
            metadata={},
        )
        recommendation = ExperimentPromotionRecommendation.objects.create(
            run=exp_run,
            target_candidate=candidate,
            target_comparison=comparison,
            recommendation_type=ExperimentPromotionRecommendationType.PROMOTE_TO_MANUAL_REVIEW,
            rationale='Recommendation from experiment validation.',
            reason_codes=['promotion_candidate'],
            confidence=confidence,
            blockers=[],
            metadata={},
        )
        return exp_run, candidate, comparison, recommendation

    def test_case_building_from_valid_comparison(self):
        exp_run, _, _, _ = self._create_candidate_bundle(
            sample_count=120,
            comparison_status='IMPROVED',
            confidence=Decimal('0.88'),
        )
        response = self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PromotionCase.objects.count(), 1)
        case = PromotionCase.objects.latest('id')
        self.assertEqual(case.target_component, 'calibration')

    def test_needs_more_data_when_validation_is_weak(self):
        exp_run, _, _, _ = self._create_candidate_bundle(
            sample_count=18,
            comparison_status='NEEDS_MORE_DATA',
            confidence=Decimal('0.41'),
        )
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        case = PromotionCase.objects.latest('id')
        recommendation = PromotionDecisionRecommendation.objects.filter(target_case=case).latest('id')
        self.assertEqual(case.case_status, PromotionCaseStatus.NEEDS_MORE_DATA)
        self.assertEqual(recommendation.recommendation_type, PromotionDecisionRecommendationType.DEFER_FOR_MORE_EVIDENCE)

    def test_approve_for_manual_adoption_when_evidence_is_strong(self):
        exp_run, _, _, _ = self._create_candidate_bundle(
            sample_count=160,
            comparison_status='IMPROVED',
            confidence=Decimal('0.92'),
        )
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        case = PromotionCase.objects.latest('id')
        recommendation = PromotionDecisionRecommendation.objects.filter(target_case=case).latest('id')
        self.assertEqual(case.case_status, PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION)
        self.assertEqual(recommendation.recommendation_type, PromotionDecisionRecommendationType.APPROVE_FOR_MANUAL_ADOPTION)

    def test_group_with_related_changes_is_generated(self):
        exp_run, *_ = self._create_candidate_bundle(
            sample_count=110,
            comparison_status='IMPROVED',
            confidence=Decimal('0.75'),
            scope='provider',
        )
        self._create_candidate_bundle(
            sample_count=115,
            comparison_status='MIXED',
            confidence=Decimal('0.60'),
            scope='provider',
        )
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        exists = PromotionDecisionRecommendation.objects.filter(
            recommendation_type=PromotionDecisionRecommendationType.GROUP_WITH_RELATED_CHANGES
        ).exists()
        self.assertTrue(exists)

    def test_summary_endpoint(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=140, comparison_status='IMPROVED', confidence=Decimal('0.85'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        response = self.client.get(reverse('promotion_committee:governed-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('cases_reviewed', payload)
        self.assertIn('recommendation_summary', payload)
