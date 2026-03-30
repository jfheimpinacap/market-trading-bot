from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.promotion_committee.models import PromotionReviewRun
from apps.promotion_committee.serializers import (
    AdoptionActionCandidateSerializer,
    AdoptionActionRecommendationSerializer,
    AdoptionRollbackPlanSerializer,
    CheckpointOutcomeRecordSerializer,
    CheckpointOutcomeRequestSerializer,
    GovernedPromotionRunRequestSerializer,
    ManualAdoptionActionSerializer,
    PostRolloutStatusSerializer,
    PromotionApplyRequestSerializer,
    PromotionAdoptionRunSerializer,
    PromotionRollbackRequestSerializer,
    PromotionCaseSerializer,
    PromotionDecisionRecommendationSerializer,
    PromotionEvidencePackSerializer,
    PromotionReviewCycleRunSerializer,
    PromotionReviewRequestSerializer,
    PromotionReviewRunSerializer,
    RolloutActionCandidateSerializer,
    RolloutCheckpointPlanSerializer,
    RolloutExecutionActionSerializer,
    RolloutExecutionRecommendationSerializer,
    RolloutExecutionRecordSerializer,
    RolloutExecutionRunSerializer,
    RolloutPreparationRecommendationSerializer,
    RolloutPreparationRunSerializer,
    ManualRollbackExecutionSerializer,
    ManualRolloutPlanSerializer,
)
from apps.promotion_committee.services import (
    apply_review_decision,
    apply_manual_adoption_case,
    build_adoption_summary,
    build_promotion_summary,
    get_current_recommendation,
    run_governed_promotion_review,
    run_promotion_adoption_review,
    run_promotion_review,
    run_rollout_preparation,
    build_rollout_preparation_summary,
    execute_manual_rollback,
    build_rollout_execution_summary,
    close_rollout_execution,
    consolidate_post_rollout_status,
    execute_rollout_plan,
    record_checkpoint_outcome,
    run_rollout_execution_review,
    generate_execution_recommendations,
)
from apps.promotion_committee.models import (
    AdoptionActionCandidate,
    AdoptionActionRecommendation,
    AdoptionRollbackPlan,
    ManualAdoptionAction,
    PromotionCase,
    PromotionDecisionRecommendation,
    PromotionEvidencePack,
    PromotionReviewCycleRun,
    RolloutActionCandidate,
    ManualRolloutPlan,
    RolloutCheckpointPlan,
    ManualRollbackExecution,
    RolloutPreparationRecommendation,
    RolloutPreparationRun,
    CheckpointOutcomeRecord,
    PostRolloutStatus,
    RolloutExecutionRecommendation,
    RolloutExecutionRecord,
    RolloutExecutionRun,
)


class PromotionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = PromotionReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_promotion_review(
            challenger_binding_id=serializer.validated_data.get('challenger_binding_id'),
            decision_mode=serializer.validated_data.get('decision_mode', 'RECOMMENDATION_ONLY'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(PromotionReviewRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PromotionRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PromotionReviewRunSerializer

    def get_queryset(self):
        return PromotionReviewRun.objects.select_related('evidence_snapshot__champion_binding', 'evidence_snapshot__challenger_binding').prefetch_related('decision_logs').order_by('-created_at', '-id')[:50]


class PromotionRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PromotionReviewRunSerializer
    queryset = PromotionReviewRun.objects.select_related('evidence_snapshot__champion_binding', 'evidence_snapshot__challenger_binding').prefetch_related('decision_logs').order_by('-created_at', '-id')


class CurrentPromotionRecommendationView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        run = get_current_recommendation()
        return Response({'current_recommendation': PromotionReviewRunSerializer(run).data if run else None}, status=status.HTTP_200_OK)


class PromotionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_promotion_summary()
        return Response(
            {
                'latest_run': PromotionReviewRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'total_runs': summary['total_runs'],
                'recommendation_counts': summary['recommendation_counts'],
                'is_recommendation_stale': summary['is_recommendation_stale'],
            },
            status=status.HTTP_200_OK,
        )


class PromotionApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        run = PromotionReviewRun.objects.select_related('evidence_snapshot__challenger_binding').get(pk=pk)
        serializer = PromotionApplyRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            run = apply_review_decision(review_run=run, actor=serializer.validated_data['actor'], notes=serializer.validated_data.get('notes', ''))
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PromotionReviewRunSerializer(run).data, status=status.HTTP_200_OK)


class GovernedPromotionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = GovernedPromotionRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_governed_promotion_review(
            actor=serializer.validated_data.get('actor', 'promotion_ui'),
            linked_experiment_run_id=serializer.validated_data.get('linked_experiment_run_id'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(PromotionReviewCycleRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PromotionCasesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PromotionCaseSerializer

    def get_queryset(self):
        queryset = PromotionCase.objects.select_related(
            'review_run', 'linked_experiment_candidate', 'linked_comparison', 'linked_tuning_proposal', 'linked_bundle'
        ).order_by('-created_at', '-id')
        if self.request.query_params.get('target_component'):
            queryset = queryset.filter(target_component=self.request.query_params['target_component'])
        if self.request.query_params.get('target_scope'):
            queryset = queryset.filter(target_scope=self.request.query_params['target_scope'])
        if self.request.query_params.get('case_status'):
            queryset = queryset.filter(case_status=self.request.query_params['case_status'])
        if self.request.query_params.get('priority_level'):
            queryset = queryset.filter(priority_level=self.request.query_params['priority_level'])
        return queryset[:200]


class PromotionEvidencePacksView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PromotionEvidencePackSerializer

    def get_queryset(self):
        return PromotionEvidencePack.objects.select_related('linked_promotion_case').order_by('-created_at', '-id')[:200]


class PromotionDecisionRecommendationsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PromotionDecisionRecommendationSerializer

    def get_queryset(self):
        return PromotionDecisionRecommendation.objects.select_related('review_run', 'target_case').order_by('-created_at', '-id')[:200]


class GovernedPromotionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest = PromotionReviewCycleRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': PromotionReviewCycleRunSerializer(latest).data if latest else None,
                'cases_reviewed': latest.candidate_count if latest else 0,
                'ready_for_review': latest.ready_for_review_count if latest else 0,
                'needs_more_data': latest.needs_more_data_count if latest else 0,
                'deferred': latest.deferred_count if latest else 0,
                'rejected': latest.rejected_count if latest else 0,
                'high_priority': latest.high_priority_count if latest else 0,
                'recommendation_summary': latest.recommendation_summary if latest else {},
            },
            status=status.HTTP_200_OK,
        )


class PromotionAdoptionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = GovernedPromotionRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_promotion_adoption_review(
            actor=serializer.validated_data.get('actor', 'promotion_ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(PromotionAdoptionRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PromotionAdoptionCandidatesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AdoptionActionCandidateSerializer

    def get_queryset(self):
        return AdoptionActionCandidate.objects.select_related('linked_promotion_case', 'adoption_run').order_by('-created_at', '-id')[:200]


class PromotionAdoptionActionsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ManualAdoptionActionSerializer

    def get_queryset(self):
        return ManualAdoptionAction.objects.select_related('linked_promotion_case', 'linked_candidate', 'adoption_run').order_by('-created_at', '-id')[:200]


class PromotionRollbackPlansView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AdoptionRollbackPlanSerializer

    def get_queryset(self):
        return AdoptionRollbackPlan.objects.select_related('linked_manual_action').order_by('-created_at', '-id')[:200]


class PromotionAdoptionRecommendationsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AdoptionActionRecommendationSerializer

    def get_queryset(self):
        return AdoptionActionRecommendation.objects.select_related('adoption_run', 'linked_promotion_case', 'target_action').order_by('-created_at', '-id')[:200]


class PromotionAdoptionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_adoption_summary()
        return Response(
            {
                'latest_run': PromotionAdoptionRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'approved_cases': summary['approved_cases'],
                'ready_to_apply': summary['ready_to_apply'],
                'blocked': summary['blocked'],
                'applied': summary['applied'],
                'rollback_prepared': summary['rollback_prepared'],
                'rollout_handoff_ready': summary['rollout_handoff_ready'],
                'recommendation_summary': summary['recommendation_summary'],
            },
            status=status.HTTP_200_OK,
        )


class PromotionManualApplyCaseView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, case_id: int, *args, **kwargs):
        serializer = PromotionApplyRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        promotion_case = PromotionCase.objects.get(pk=case_id)
        try:
            action = apply_manual_adoption_case(
                promotion_case=promotion_case, actor=serializer.validated_data['actor'], notes=serializer.validated_data.get('notes', '')
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ManualAdoptionActionSerializer(action).data, status=status.HTTP_200_OK)


class PromotionRunRolloutPrepView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = GovernedPromotionRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_rollout_preparation(
            actor=serializer.validated_data.get('actor', 'promotion_ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(RolloutPreparationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PromotionRolloutCandidatesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RolloutActionCandidateSerializer

    def get_queryset(self):
        return RolloutActionCandidate.objects.select_related(
            'preparation_run', 'linked_manual_adoption_action', 'linked_promotion_case'
        ).order_by('-created_at', '-id')[:200]


class PromotionRolloutPlansView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ManualRolloutPlanSerializer

    def get_queryset(self):
        return ManualRolloutPlan.objects.select_related('linked_candidate', 'linked_manual_adoption_action').order_by('-created_at', '-id')[:200]


class PromotionCheckpointPlansView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RolloutCheckpointPlanSerializer

    def get_queryset(self):
        return RolloutCheckpointPlan.objects.select_related('linked_rollout_plan').order_by('-created_at', '-id')[:300]


class PromotionRollbackExecutionsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ManualRollbackExecutionSerializer

    def get_queryset(self):
        return ManualRollbackExecution.objects.select_related(
            'linked_rollout_plan', 'linked_rollback_plan', 'linked_manual_action'
        ).order_by('-created_at', '-id')[:200]


class PromotionRolloutRecommendationsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RolloutPreparationRecommendationSerializer

    def get_queryset(self):
        return RolloutPreparationRecommendation.objects.select_related(
            'preparation_run', 'target_candidate', 'target_plan'
        ).order_by('-created_at', '-id')[:300]


class PromotionRolloutSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_rollout_preparation_summary()
        return Response(
            {
                'latest_run': RolloutPreparationRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'candidates': summary['candidates'],
                'ready': summary['ready'],
                'blocked': summary['blocked'],
                'checkpoint_plans': summary['checkpoint_plans'],
                'rollback_ready': summary['rollback_ready'],
                'rollback_executed': summary['rollback_executed'],
                'recommendation_summary': summary['recommendation_summary'],
            },
            status=status.HTTP_200_OK,
        )


class PromotionPrepareRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, case_id: int, *args, **kwargs):
        serializer = GovernedPromotionRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_rollout_preparation(
            actor=serializer.validated_data.get('actor', 'promotion_ui'),
            metadata={'target_case_id': case_id, **(serializer.validated_data.get('metadata') or {})},
        )
        plans = ManualRolloutPlan.objects.filter(linked_manual_adoption_action__linked_promotion_case_id=case_id).order_by('-created_at', '-id')
        return Response(
            {
                'run': RolloutPreparationRunSerializer(run).data,
                'plans': ManualRolloutPlanSerializer(plans[:20], many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PromotionRollbackActionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, action_id: int, *args, **kwargs):
        serializer = PromotionRollbackRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        action = ManualAdoptionAction.objects.get(pk=action_id)
        execution = execute_manual_rollback(action=action, actor=serializer.validated_data.get('actor', 'operator'))
        return Response(ManualRollbackExecutionSerializer(execution).data, status=status.HTTP_200_OK)


class PromotionRunRolloutExecutionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = GovernedPromotionRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_rollout_execution_review(
            actor=serializer.validated_data.get('actor', 'promotion_ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(RolloutExecutionRunSerializer(run).data, status=status.HTTP_201_CREATED)


class PromotionRolloutExecutionsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RolloutExecutionRecordSerializer

    def get_queryset(self):
        return RolloutExecutionRecord.objects.select_related('execution_run', 'linked_rollout_plan').order_by('-created_at', '-id')[:300]


class PromotionCheckpointOutcomesView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CheckpointOutcomeRecordSerializer

    def get_queryset(self):
        return CheckpointOutcomeRecord.objects.select_related('linked_rollout_execution', 'linked_checkpoint_plan').order_by('-created_at', '-id')[:400]


class PromotionPostRolloutStatusView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PostRolloutStatusSerializer

    def get_queryset(self):
        return PostRolloutStatus.objects.select_related('linked_rollout_execution').order_by('-created_at', '-id')[:300]


class PromotionRolloutExecutionRecommendationsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RolloutExecutionRecommendationSerializer

    def get_queryset(self):
        return RolloutExecutionRecommendation.objects.select_related('execution_run', 'target_execution').order_by('-created_at', '-id')[:300]


class PromotionRolloutExecutionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_rollout_execution_summary()
        return Response(
            {
                'latest_run': RolloutExecutionRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'rollout_plans_ready': summary['rollout_plans_ready'],
                'executions_running': summary['executions_running'],
                'healthy_rollouts': summary['healthy_rollouts'],
                'review_required': summary['review_required'],
                'rollback_recommended': summary['rollback_recommended'],
                'rollback_executed': summary['rollback_executed'],
                'recommendation_summary': summary['recommendation_summary'],
            },
            status=status.HTTP_200_OK,
        )


class PromotionExecuteRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, plan_id: int, *args, **kwargs):
        serializer = RolloutExecutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        plan = ManualRolloutPlan.objects.get(pk=plan_id)
        execution = execute_rollout_plan(
            plan=plan,
            actor=serializer.validated_data.get('actor', 'operator'),
            notes=serializer.validated_data.get('notes', ''),
            rationale=serializer.validated_data.get('rationale', ''),
        )
        status_snapshot = consolidate_post_rollout_status(execution=execution)
        generate_execution_recommendations(run=execution.execution_run)
        return Response(
            {
                'execution': RolloutExecutionRecordSerializer(execution).data,
                'post_rollout_status': PostRolloutStatusSerializer(status_snapshot).data,
            },
            status=status.HTTP_200_OK,
        )


class PromotionRecordCheckpointOutcomeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, checkpoint_id: int, *args, **kwargs):
        serializer = CheckpointOutcomeRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        checkpoint = RolloutCheckpointPlan.objects.get(pk=checkpoint_id)
        outcome = record_checkpoint_outcome(
            checkpoint_plan=checkpoint,
            outcome_status=serializer.validated_data['outcome_status'],
            observed_metrics=serializer.validated_data.get('observed_metrics') or {},
            rationale=serializer.validated_data.get('outcome_rationale', '') or 'Manual checkpoint outcome recorded.',
            actor=serializer.validated_data.get('actor', 'operator'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        status_snapshot = consolidate_post_rollout_status(execution=outcome.linked_rollout_execution)
        generate_execution_recommendations(run=outcome.linked_rollout_execution.execution_run)
        return Response(
            {
                'outcome': CheckpointOutcomeRecordSerializer(outcome).data,
                'post_rollout_status': PostRolloutStatusSerializer(status_snapshot).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PromotionCloseRolloutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, execution_id: int, *args, **kwargs):
        serializer = RolloutExecutionActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        execution = RolloutExecutionRecord.objects.get(pk=execution_id)
        execution = close_rollout_execution(
            execution=execution,
            actor=serializer.validated_data.get('actor', 'operator'),
            notes=serializer.validated_data.get('notes', ''),
        )
        status_snapshot = consolidate_post_rollout_status(execution=execution)
        generate_execution_recommendations(run=execution.execution_run)
        return Response(
            {
                'execution': RolloutExecutionRecordSerializer(execution).data,
                'post_rollout_status': PostRolloutStatusSerializer(status_snapshot).data,
            },
            status=status.HTTP_200_OK,
        )
