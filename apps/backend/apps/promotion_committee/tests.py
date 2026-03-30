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
    AdoptionRollbackPlan,
    CheckpointOutcomeRecord,
    ManualRollbackExecution,
    ManualRolloutPlan,
    ManualAdoptionAction,
    ManualAdoptionActionStatus,
    PostRolloutStatus,
    PromotionCase,
    PromotionCaseStatus,
    PromotionDecisionRecommendation,
    PromotionDecisionRecommendationType,
    RolloutExecutionRecommendation,
    RolloutExecutionStatus,
    RolloutActionCandidate,
    RolloutCheckpointPlan,
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

    def test_adoption_review_builds_candidates_actions_and_rollback(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=160, comparison_status='IMPROVED', confidence=Decimal('0.92'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        response = self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(ManualAdoptionAction.objects.count(), 1)
        self.assertGreaterEqual(AdoptionRollbackPlan.objects.count(), 1)

    def test_missing_mapping_becomes_require_target_mapping(self):
        exp_run, candidate, comparison, recommendation = self._create_candidate_bundle(
            sample_count=160,
            comparison_status='IMPROVED',
            confidence=Decimal('0.92'),
        )
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        case = PromotionCase.objects.latest('id')
        case.current_value = ''
        case.proposed_value = ''
        case.save(update_fields=['current_value', 'proposed_value', 'updated_at'])
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        action = ManualAdoptionAction.objects.filter(linked_promotion_case=case).latest('id')
        self.assertEqual(action.action_type, 'REQUIRE_TARGET_MAPPING')
        self.assertEqual(action.action_status, ManualAdoptionActionStatus.BLOCKED)

    def test_adoption_summary_and_manual_apply_endpoint(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=160, comparison_status='IMPROVED', confidence=Decimal('0.92'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        case = PromotionCase.objects.latest('id')
        action = ManualAdoptionAction.objects.filter(linked_promotion_case=case).latest('id')
        self.assertEqual(action.action_status, ManualAdoptionActionStatus.READY_TO_APPLY)
        apply_response = self.client.post(reverse('promotion_committee:apply', kwargs={'case_id': case.id}), {'actor': 'tester'}, format='json')
        self.assertEqual(apply_response.status_code, 200)
        summary_response = self.client.get(reverse('promotion_committee:adoption-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('ready_to_apply', summary_response.json())

    def test_run_rollout_prep_creates_candidates_plans_and_checkpoints(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=170, comparison_status='IMPROVED', confidence=Decimal('0.91'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')

        response = self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(RolloutActionCandidate.objects.count(), 1)
        self.assertGreaterEqual(ManualRolloutPlan.objects.count(), 1)
        self.assertGreaterEqual(RolloutCheckpointPlan.objects.count(), 1)

    def test_rollout_prep_blocks_when_target_mapping_incomplete(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=160, comparison_status='IMPROVED', confidence=Decimal('0.92'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        action = ManualAdoptionAction.objects.latest('id')
        action.current_value_snapshot = {}
        action.proposed_value_snapshot = {}
        action.save(update_fields=['current_value_snapshot', 'proposed_value_snapshot', 'updated_at'])

        self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')
        candidate = RolloutActionCandidate.objects.get(linked_manual_adoption_action=action)
        self.assertFalse(candidate.ready_for_rollout)
        self.assertIn('missing_snapshots', candidate.blockers)

    def test_rollout_summary_and_manual_rollback_endpoint(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=170, comparison_status='IMPROVED', confidence=Decimal('0.91'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')
        action = ManualAdoptionAction.objects.latest('id')

        rollback_response = self.client.post(reverse('promotion_committee:rollback-action', kwargs={'action_id': action.id}), {}, format='json')
        self.assertEqual(rollback_response.status_code, 200)
        self.assertTrue(ManualRollbackExecution.objects.filter(linked_manual_action=action).exists())

        summary_response = self.client.get(reverse('promotion_committee:rollout-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('checkpoint_plans', summary_response.json())

    def test_rollout_execution_review_creates_execution_records_from_ready_plans(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=170, comparison_status='IMPROVED', confidence=Decimal('0.91'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')

        response = self.client.post(reverse('promotion_committee:run-rollout-execution'), {}, format='json')
        self.assertEqual(response.status_code, 201)
        execution_list = self.client.get(reverse('promotion_committee:rollout-executions'))
        self.assertEqual(execution_list.status_code, 200)
        self.assertGreaterEqual(len(execution_list.json()), 1)

    def test_checkpoint_outcome_post_rollout_status_and_rollback_recommendation(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=170, comparison_status='IMPROVED', confidence=Decimal('0.91'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-execution'), {}, format='json')
        plan = ManualRolloutPlan.objects.latest('id')

        execute_response = self.client.post(reverse('promotion_committee:execute-rollout', kwargs={'plan_id': plan.id}), {}, format='json')
        self.assertEqual(execute_response.status_code, 200)

        checkpoint = RolloutCheckpointPlan.objects.filter(linked_rollout_plan=plan).first()
        outcome_response = self.client.post(
            reverse('promotion_committee:record-checkpoint-outcome', kwargs={'checkpoint_id': checkpoint.id}),
            {'outcome_status': 'WARNING', 'outcome_rationale': 'Manual warning'},
            format='json',
        )
        self.assertEqual(outcome_response.status_code, 201)
        self.assertTrue(CheckpointOutcomeRecord.objects.filter(linked_checkpoint_plan=checkpoint).exists())
        self.assertEqual(PostRolloutStatus.objects.latest('id').status, 'CAUTION')

        checkpoint.checkpoint_type = 'rollback_readiness_check'
        checkpoint.save(update_fields=['checkpoint_type', 'updated_at'])
        rollback_outcome = self.client.post(
            reverse('promotion_committee:record-checkpoint-outcome', kwargs={'checkpoint_id': checkpoint.id}),
            {'outcome_status': 'FAILED', 'outcome_rationale': 'Critical rollback trigger'},
            format='json',
        )
        self.assertEqual(rollback_outcome.status_code, 201)
        self.assertEqual(PostRolloutStatus.objects.latest('id').status, 'ROLLBACK_RECOMMENDED')
        self.assertTrue(RolloutExecutionRecommendation.objects.filter(recommendation_type='RECOMMEND_MANUAL_ROLLBACK').exists())

    def test_rollout_execution_summary_endpoint(self):
        exp_run, *_ = self._create_candidate_bundle(sample_count=170, comparison_status='IMPROVED', confidence=Decimal('0.91'))
        self.client.post(reverse('promotion_committee:governed-run-review'), {'linked_experiment_run_id': exp_run.id}, format='json')
        self.client.post(reverse('promotion_committee:run-adoption-review'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-prep'), {}, format='json')
        self.client.post(reverse('promotion_committee:run-rollout-execution'), {}, format='json')
        response = self.client.get(reverse('promotion_committee:rollout-execution-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('rollout_plans_ready', payload)
        self.assertIn('healthy_rollouts', payload)
