from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.certification_board.models import (
    BaselineResponseActionRun,
    ResponseActionCandidate,
    ResponseActionRecommendation,
    ResponseCaseTrackingRecord,
    ResponseCaseDownstreamStatus,
    ResponseRoutingAction,
    ResponseRoutingActionStatus,
    BaselineResponseCase,
    BaselineResponseRecommendation,
    BaselineResponseRun,
    ResponseEvidencePack,
    ResponseRoutingDecision,
    BaselineHealthCandidate,
    BaselineHealthRecommendation,
    BaselineHealthRun,
    BaselineHealthSignal,
    BaselineHealthStatus,
    ActivePaperBindingRecord,
    BaselineActivationCandidate,
    BaselineActivationRecommendation,
    BaselineActivationRun,
    BaselineBindingSnapshot,
    BaselineConfirmationCandidate,
    BaselineConfirmationRecommendation,
    BaselineConfirmationRun,
    CertificationCandidate,
    CertificationDecision,
    CertificationDecisionStatus,
    CertificationEvidencePack,
    CertificationRecommendation,
    CertificationRun,
    PaperBaselineActivation,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
    RolloutCertificationRun,
)
from apps.certification_board.serializers import (
    ActivatePaperBaselineRequestSerializer,
    ActivePaperBindingRecordSerializer,
    ApplyCertificationDecisionRequestSerializer,
    BaselineActivationCandidateSerializer,
    BaselineActivationRecommendationSerializer,
    BaselineActivationRunSerializer,
    BaselineHealthCandidateSerializer,
    BaselineHealthRecommendationSerializer,
    BaselineHealthRunSerializer,
    BaselineResponseCaseSerializer,
    BaselineResponseRecommendationSerializer,
    BaselineResponseRunSerializer,
    BaselineHealthSignalSerializer,
    BaselineHealthStatusSerializer,
    BaselineBindingSnapshotSerializer,
    BaselineConfirmationCandidateSerializer,
    BaselineConfirmationRecommendationSerializer,
    BaselineConfirmationRunSerializer,
    ConfirmPaperBaselineRequestSerializer,
    PaperBaselineActivationSerializer,
    PaperBaselineConfirmationSerializer,
    CertificationCandidateSerializer,
    CertificationDecisionSerializer,
    CertificationEvidencePackSerializer,
    CertificationRecommendationSerializer,
    CertificationRunSerializer,
    RolloutCertificationRunSerializer,
    RollbackBaselineActivationRequestSerializer,
    RunBaselineActivationReviewRequestSerializer,
    RunBaselineHealthReviewRequestSerializer,
    RunBaselineResponseReviewRequestSerializer,
    RunBaselineResponseActionsRequestSerializer,
    RouteResponseCaseRequestSerializer,
    UpdateResponseTrackingRequestSerializer,
    RunBaselineConfirmationReviewRequestSerializer,
    RunPostRolloutReviewRequestSerializer,
    RunCertificationReviewRequestSerializer,
    ResponseEvidencePackSerializer,
    ResponseRoutingDecisionSerializer,
    BaselineResponseActionRunSerializer,
    ResponseActionCandidateSerializer,
    ResponseRoutingActionSerializer,
    ResponseCaseTrackingRecordSerializer,
    ResponseActionRecommendationSerializer,
)
from apps.certification_board.services import (
    activate_paper_baseline,
    apply_certification_decision,
    build_certification_summary,
    confirm_paper_baseline,
    get_current_certification,
    prepare_baseline_rollback,
    rollback_baseline_activation,
    run_baseline_health_review,
    run_baseline_response_actions,
    build_baseline_response_summary,
    build_baseline_response_action_summary,
    create_tracking_record,
    run_baseline_response_review,
    run_baseline_activation_review,
    run_baseline_confirmation_review,
    run_post_rollout_certification_review,
    run_certification_review,
)
from django.utils import timezone


class CertificationRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCertificationReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_certification_review(
            decision_mode=serializer.validated_data.get('decision_mode', 'RECOMMENDATION_ONLY'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(CertificationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class CertificationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationRunSerializer

    def get_queryset(self):
        return CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').prefetch_related('decision_logs').order_by('-created_at', '-id')[:50]


class CertificationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationRunSerializer
    queryset = CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').prefetch_related('decision_logs').order_by('-created_at', '-id')


class CurrentCertificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        run = get_current_certification()
        return Response({'current_certification': CertificationRunSerializer(run).data if run else None}, status=status.HTTP_200_OK)


class CertificationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_certification_summary()
        latest_rollout_review = RolloutCertificationRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': CertificationRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'recent_runs': CertificationRunSerializer(summary['recent_runs'], many=True).data,
                'total_runs': summary['total_runs'],
                'level_counts': summary['level_counts'],
                'recommendation_counts': summary['recommendation_counts'],
                'post_rollout_review': RolloutCertificationRunSerializer(latest_rollout_review).data if latest_rollout_review else None,
            },
            status=status.HTTP_200_OK,
        )


class CertificationApplyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        run = CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').get(pk=pk)
        serializer = ApplyCertificationDecisionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            run = apply_certification_decision(
                run=run,
                actor=serializer.validated_data['actor'],
                apply_safe_state=serializer.validated_data.get('apply_safe_state', False),
                notes=serializer.validated_data.get('notes', ''),
            )
        except ValidationError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CertificationRunSerializer(run).data, status=status.HTTP_200_OK)


class RunPostRolloutCertificationReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunPostRolloutReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        metadata = serializer.validated_data.get('metadata') or {}
        if serializer.validated_data.get('rollout_execution_run_id'):
            metadata['rollout_execution_run_id'] = serializer.validated_data['rollout_execution_run_id']
        result = run_post_rollout_certification_review(actor=serializer.validated_data['actor'], metadata=metadata)
        return Response(
            {
                'run': RolloutCertificationRunSerializer(result['run']).data,
                'candidate_count': len(result['candidates']),
                'evidence_pack_count': len(result['evidence_packs']),
                'decision_count': len(result['decisions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class CertificationCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationCandidateSerializer

    def get_queryset(self):
        return CertificationCandidate.objects.select_related(
            'review_run', 'linked_rollout_execution', 'linked_post_rollout_status', 'linked_rollout_plan', 'linked_promotion_case'
        ).order_by('-created_at', '-id')[:500]


class CertificationEvidencePackListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationEvidencePackSerializer

    def get_queryset(self):
        return CertificationEvidencePack.objects.select_related('linked_candidate').order_by('-created_at', '-id')[:500]


class CertificationDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationDecisionSerializer

    def get_queryset(self):
        return CertificationDecision.objects.select_related('linked_candidate', 'linked_evidence_pack').order_by('-created_at', '-id')[:500]


class CertificationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CertificationRecommendationSerializer

    def get_queryset(self):
        return CertificationRecommendation.objects.select_related('review_run', 'target_candidate').order_by('-created_at', '-id')[:500]


class PostRolloutCertificationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = RolloutCertificationRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': RolloutCertificationRunSerializer(latest_run).data if latest_run else None,
                'candidate_count': latest_run.candidate_count if latest_run else 0,
                'certified_count': latest_run.certified_count if latest_run else 0,
                'observation_count': latest_run.observation_count if latest_run else 0,
                'review_required_count': latest_run.review_required_count if latest_run else 0,
                'rollback_recommended_count': latest_run.rollback_recommended_count if latest_run else 0,
                'rejected_count': latest_run.rejected_count if latest_run else 0,
                'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
                'decision_counts': {
                    'certified_for_paper_baseline': CertificationDecision.objects.filter(
                        decision_status=CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE
                    ).count(),
                    'keep_under_observation': CertificationDecision.objects.filter(
                        decision_status=CertificationDecisionStatus.KEEP_UNDER_OBSERVATION
                    ).count(),
                    'require_manual_review': CertificationDecision.objects.filter(
                        decision_status=CertificationDecisionStatus.REQUIRE_MANUAL_REVIEW
                    ).count(),
                    'recommend_rollback': CertificationDecision.objects.filter(
                        decision_status=CertificationDecisionStatus.RECOMMEND_ROLLBACK
                    ).count(),
                    'reject_certification': CertificationDecision.objects.filter(
                        decision_status=CertificationDecisionStatus.REJECT_CERTIFICATION
                    ).count(),
                },
            },
            status=status.HTTP_200_OK,
        )


class RunBaselineConfirmationReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunBaselineConfirmationReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_baseline_confirmation_review(
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run': BaselineConfirmationRunSerializer(result['run']).data,
                'candidate_count': len(result['candidates']),
                'confirmation_count': len(result['confirmations']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class BaselineConfirmationCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineConfirmationCandidateSerializer

    def get_queryset(self):
        return BaselineConfirmationCandidate.objects.select_related(
            'review_run',
            'linked_certification_decision',
            'linked_certification_candidate',
            'linked_rollout_execution',
        ).order_by('-created_at', '-id')[:500]


class PaperBaselineConfirmationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperBaselineConfirmationSerializer

    def get_queryset(self):
        return PaperBaselineConfirmation.objects.select_related(
            'linked_candidate', 'linked_certification_decision'
        ).order_by('-created_at', '-id')[:500]


class BaselineBindingSnapshotListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineBindingSnapshotSerializer

    def get_queryset(self):
        return BaselineBindingSnapshot.objects.select_related('linked_confirmation').order_by('-created_at', '-id')[:500]


class BaselineConfirmationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineConfirmationRecommendationSerializer

    def get_queryset(self):
        return BaselineConfirmationRecommendation.objects.select_related(
            'review_run', 'target_confirmation'
        ).order_by('-created_at', '-id')[:500]


class BaselineConfirmationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = BaselineConfirmationRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': BaselineConfirmationRunSerializer(latest_run).data if latest_run else None,
                'candidate_count': latest_run.candidate_count if latest_run else 0,
                'ready_to_confirm_count': latest_run.ready_to_confirm_count if latest_run else 0,
                'blocked_count': latest_run.blocked_count if latest_run else 0,
                'confirmed_count': latest_run.confirmed_count if latest_run else 0,
                'rollback_ready_count': latest_run.rollback_ready_count if latest_run else 0,
                'binding_review_required_count': BaselineConfirmationRecommendation.objects.filter(
                    recommendation_type='REQUIRE_BINDING_REVIEW'
                ).count(),
                'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
            },
            status=status.HTTP_200_OK,
        )


class ConfirmPaperBaselineView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, decision_id: int, *args, **kwargs):
        serializer = ConfirmPaperBaselineRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        confirmation = confirm_paper_baseline(
            decision_id=decision_id,
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            rationale=serializer.validated_data.get('rationale', ''),
        )
        return Response(PaperBaselineConfirmationSerializer(confirmation).data, status=status.HTTP_200_OK)


class RollbackPaperBaselineView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, confirmation_id: int, *args, **kwargs):
        confirmation = PaperBaselineConfirmation.objects.get(pk=confirmation_id)
        actor = (request.data or {}).get('actor', 'operator-ui')
        confirmation = prepare_baseline_rollback(confirmation=confirmation, actor=actor)
        return Response(PaperBaselineConfirmationSerializer(confirmation).data, status=status.HTTP_200_OK)


class RunBaselineActivationReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunBaselineActivationReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_baseline_activation_review(
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run': BaselineActivationRunSerializer(result['run']).data,
                'candidate_count': len(result['candidates']),
                'activation_count': len(result['activations']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class BaselineActivationCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineActivationCandidateSerializer

    def get_queryset(self):
        return BaselineActivationCandidate.objects.select_related(
            'review_run', 'linked_paper_baseline_confirmation', 'linked_certification_decision'
        ).order_by('-created_at', '-id')[:500]


class PaperBaselineActivationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = PaperBaselineActivationSerializer

    def get_queryset(self):
        return PaperBaselineActivation.objects.select_related('linked_candidate', 'linked_confirmation').order_by('-created_at', '-id')[:500]


class ActivePaperBindingRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ActivePaperBindingRecordSerializer

    def get_queryset(self):
        return ActivePaperBindingRecord.objects.select_related('source_activation').order_by('-created_at', '-id')[:500]


class BaselineActivationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineActivationRecommendationSerializer

    def get_queryset(self):
        return BaselineActivationRecommendation.objects.select_related('review_run', 'target_activation').order_by('-created_at', '-id')[:500]


class BaselineActivationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = BaselineActivationRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': BaselineActivationRunSerializer(latest_run).data if latest_run else None,
                'confirmed_baselines': PaperBaselineConfirmation.objects.filter(
                    confirmation_status=PaperBaselineConfirmationStatus.CONFIRMED
                ).count(),
                'candidate_count': latest_run.candidate_count if latest_run else 0,
                'ready_to_activate_count': latest_run.ready_to_activate_count if latest_run else 0,
                'blocked_count': latest_run.blocked_count if latest_run else 0,
                'activated_count': latest_run.activated_count if latest_run else 0,
                'rollback_available_count': latest_run.rollback_ready_count if latest_run else 0,
                'binding_recheck_required_count': BaselineActivationRecommendation.objects.filter(
                    recommendation_type='REQUIRE_BINDING_RECHECK'
                ).count(),
                'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
            },
            status=status.HTTP_200_OK,
        )


class RunBaselineHealthReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunBaselineHealthReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_baseline_health_review(
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run': BaselineHealthRunSerializer(result['run']).data,
                'candidate_count': len(result['candidates']),
                'status_count': len(result['statuses']),
                'signal_count': len(result['signals']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class BaselineHealthCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineHealthCandidateSerializer

    def get_queryset(self):
        return BaselineHealthCandidate.objects.select_related(
            'review_run',
            'linked_active_binding',
            'linked_baseline_activation',
        ).order_by('-created_at', '-id')[:500]


class BaselineHealthStatusListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineHealthStatusSerializer

    def get_queryset(self):
        return BaselineHealthStatus.objects.select_related(
            'linked_candidate',
            'linked_candidate__review_run',
            'linked_candidate__linked_active_binding',
        ).order_by('-created_at', '-id')[:500]


class BaselineHealthSignalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineHealthSignalSerializer

    def get_queryset(self):
        return BaselineHealthSignal.objects.select_related(
            'linked_status',
            'linked_status__linked_candidate',
        ).order_by('-created_at', '-id')[:1000]


class BaselineHealthRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineHealthRecommendationSerializer

    def get_queryset(self):
        return BaselineHealthRecommendation.objects.select_related(
            'review_run',
            'target_status',
            'target_status__linked_candidate',
        ).order_by('-created_at', '-id')[:500]


class BaselineHealthSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = BaselineHealthRun.objects.order_by('-started_at', '-id').first()
        return Response(
            {
                'latest_run': BaselineHealthRunSerializer(latest_run).data if latest_run else None,
                'active_baselines_reviewed': latest_run.active_binding_count if latest_run else 0,
                'healthy_count': latest_run.healthy_count if latest_run else 0,
                'under_watch_count': latest_run.watch_count if latest_run else 0,
                'degraded_count': latest_run.degraded_count if latest_run else 0,
                'review_required_count': latest_run.review_required_count if latest_run else 0,
                'rollback_review_recommended_count': latest_run.rollback_review_count if latest_run else 0,
                'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
            },
            status=status.HTTP_200_OK,
        )


class RunBaselineResponseReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunBaselineResponseReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_baseline_response_review(
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run': BaselineResponseRunSerializer(result['run']).data,
                'case_count': len(result['cases']),
                'evidence_pack_count': len(result['evidence_packs']),
                'routing_decision_count': len(result['routing_decisions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class BaselineResponseCaseListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineResponseCaseSerializer

    def get_queryset(self):
        return BaselineResponseCase.objects.select_related(
            'review_run',
            'linked_active_binding',
            'linked_baseline_health_status',
        ).order_by('-created_at', '-id')[:500]


class ResponseEvidencePackListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseEvidencePackSerializer

    def get_queryset(self):
        return ResponseEvidencePack.objects.select_related(
            'linked_response_case',
            'linked_health_status',
        ).order_by('-created_at', '-id')[:500]


class ResponseRoutingDecisionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseRoutingDecisionSerializer

    def get_queryset(self):
        return ResponseRoutingDecision.objects.select_related('linked_response_case').order_by('-created_at', '-id')[:500]


class BaselineResponseRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BaselineResponseRecommendationSerializer

    def get_queryset(self):
        return BaselineResponseRecommendation.objects.select_related('review_run', 'target_case').order_by('-created_at', '-id')[:500]


class BaselineResponseSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_baseline_response_summary()
        return Response(
            {
                'latest_run': BaselineResponseRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'active_baselines_reviewed': summary['active_baselines_reviewed'],
                'open_response_cases': summary['open_response_cases'],
                'reevaluation_case_count': summary['reevaluation_case_count'],
                'tuning_case_count': summary['tuning_case_count'],
                'rollback_review_case_count': summary['rollback_review_case_count'],
                'watch_case_count': summary['watch_case_count'],
                'recommendation_summary': summary['recommendation_summary'],
                'case_status_summary': summary['case_status_summary'],
                'routing_status_summary': summary['routing_status_summary'],
                'evidence_status_summary': summary['evidence_status_summary'],
                'recommendation_type_summary': summary['recommendation_type_summary'],
            },
            status=status.HTTP_200_OK,
        )


class RunBaselineResponseActionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunBaselineResponseActionsRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_baseline_response_actions(
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(
            {
                'run': BaselineResponseActionRunSerializer(result['run']).data,
                'candidate_count': len(result['candidates']),
                'routing_action_count': len(result['actions']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_201_CREATED,
        )


class ResponseActionCandidateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseActionCandidateSerializer

    def get_queryset(self):
        return ResponseActionCandidate.objects.select_related(
            'action_run',
            'linked_response_case',
            'linked_routing_decision',
        ).order_by('-created_at', '-id')[:500]


class ResponseRoutingActionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseRoutingActionSerializer

    def get_queryset(self):
        return ResponseRoutingAction.objects.select_related(
            'linked_candidate',
            'linked_response_case',
        ).order_by('-created_at', '-id')[:500]


class ResponseCaseTrackingRecordListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseCaseTrackingRecordSerializer

    def get_queryset(self):
        return ResponseCaseTrackingRecord.objects.select_related(
            'linked_response_case',
            'linked_routing_action',
        ).order_by('-created_at', '-id')[:500]


class ResponseActionRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ResponseActionRecommendationSerializer

    def get_queryset(self):
        return ResponseActionRecommendation.objects.select_related('action_run', 'target_action').order_by('-created_at', '-id')[:500]


class BaselineResponseActionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = build_baseline_response_action_summary()
        return Response(
            {
                'latest_run': BaselineResponseActionRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
                'response_cases_reviewed': summary['response_cases_reviewed'],
                'ready_to_route': summary['ready_to_route'],
                'routed': summary['routed'],
                'blocked': summary['blocked'],
                'under_review': summary['under_review'],
                'closed': summary['closed'],
                'recommendation_summary': summary['recommendation_summary'],
                'action_status_summary': summary['action_status_summary'],
                'recommendation_type_summary': summary['recommendation_type_summary'],
            },
            status=status.HTTP_200_OK,
        )


class RouteResponseCaseView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, case_id: int, *args, **kwargs):
        response_case = BaselineResponseCase.objects.get(pk=case_id)
        serializer = RouteResponseCaseRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        action = ResponseRoutingAction.objects.filter(
            linked_response_case=response_case,
            action_status__in=[ResponseRoutingActionStatus.READY_TO_ROUTE, ResponseRoutingActionStatus.PROPOSED],
        ).order_by('-created_at', '-id').first()
        if action is None:
            return Response({'detail': 'No route-ready action exists for this case.'}, status=status.HTTP_400_BAD_REQUEST)
        action.action_type = payload.get('action_type') or action.action_type
        action.routing_target = payload.get('routing_target') or action.routing_target
        action.rationale = payload.get('rationale') or action.rationale
        action.reason_codes = payload.get('reason_codes') or action.reason_codes
        action.routed_by = payload.get('routed_by', 'operator-ui')
        action.routed_at = timezone.now()
        action.linked_target_artifact = payload.get('linked_target_artifact') or action.linked_target_artifact
        action.action_status = ResponseRoutingActionStatus.ROUTED
        action.metadata = {**(action.metadata or {}), **(payload.get('metadata') or {}), 'manual_routed': True}
        action.save()

        tracking = create_tracking_record(
            response_case=response_case,
            routing_action=action,
            downstream_status=ResponseCaseDownstreamStatus.SENT,
            tracking_notes='Manual handoff executed.',
            tracked_by=action.routed_by,
            linked_downstream_reference=action.linked_target_artifact,
            metadata={'source': 'route-response-case'},
        )
        return Response(
            {
                'routing_action': ResponseRoutingActionSerializer(action).data,
                'tracking_record': ResponseCaseTrackingRecordSerializer(tracking).data,
            },
            status=status.HTTP_200_OK,
        )


class UpdateResponseTrackingView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, case_id: int, *args, **kwargs):
        response_case = BaselineResponseCase.objects.get(pk=case_id)
        serializer = UpdateResponseTrackingRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        action = ResponseRoutingAction.objects.filter(linked_response_case=response_case).order_by('-created_at', '-id').first()
        tracking = create_tracking_record(
            response_case=response_case,
            routing_action=action,
            downstream_status=payload['downstream_status'],
            tracking_notes=payload.get('tracking_notes', ''),
            tracked_by=payload.get('tracked_by', 'operator-ui'),
            linked_downstream_reference=payload.get('linked_downstream_reference', ''),
            metadata=payload.get('metadata') or {},
        )
        if payload['downstream_status'] in {
            ResponseCaseDownstreamStatus.COMPLETED,
            ResponseCaseDownstreamStatus.CLOSED_NO_ACTION,
        } and action:
            action.action_status = ResponseRoutingActionStatus.CLOSED
            action.save(update_fields=['action_status', 'updated_at'])
        return Response(ResponseCaseTrackingRecordSerializer(tracking).data, status=status.HTTP_200_OK)


class ActivatePaperBaselineView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, confirmation_id: int, *args, **kwargs):
        serializer = ActivatePaperBaselineRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        activation = activate_paper_baseline(
            confirmation_id=confirmation_id,
            actor=serializer.validated_data.get('actor', 'operator-ui'),
            rationale=serializer.validated_data.get('rationale', ''),
        )
        return Response(PaperBaselineActivationSerializer(activation).data, status=status.HTTP_200_OK)


class RollbackBaselineActivationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, activation_id: int, *args, **kwargs):
        serializer = RollbackBaselineActivationRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        activation = rollback_baseline_activation(
            activation_id=activation_id,
            actor=serializer.validated_data.get('actor', 'operator-ui'),
        )
        return Response(PaperBaselineActivationSerializer(activation).data, status=status.HTTP_200_OK)
