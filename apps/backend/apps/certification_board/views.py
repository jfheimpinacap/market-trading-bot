from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.certification_board.models import CertificationRun
from apps.certification_board.serializers import (
    BaselineBindingSnapshotSerializer,
    BaselineConfirmationCandidateSerializer,
    BaselineConfirmationRecommendationSerializer,
    BaselineConfirmationRunSerializer,
    ConfirmPaperBaselineRequestSerializer,
    PaperBaselineConfirmationSerializer,
    ApplyCertificationDecisionRequestSerializer,
    CertificationCandidateSerializer,
    CertificationDecisionSerializer,
    CertificationEvidencePackSerializer,
    CertificationRecommendationSerializer,
    CertificationRunSerializer,
    RolloutCertificationRunSerializer,
    RunBaselineConfirmationReviewRequestSerializer,
    RunPostRolloutReviewRequestSerializer,
    RunCertificationReviewRequestSerializer,
)
from apps.certification_board.services import (
    apply_certification_decision,
    build_certification_summary,
    confirm_paper_baseline,
    get_current_certification,
    prepare_baseline_rollback,
    run_baseline_confirmation_review,
    run_post_rollout_certification_review,
    run_certification_review,
)
from apps.certification_board.models import (
    BaselineBindingSnapshot,
    BaselineConfirmationCandidate,
    BaselineConfirmationRecommendation,
    BaselineConfirmationRun,
    CertificationCandidate,
    CertificationDecision,
    CertificationEvidencePack,
    CertificationRecommendation,
    CertificationDecisionStatus,
    PaperBaselineConfirmation,
    PaperBaselineConfirmationStatus,
    RolloutCertificationRun,
)


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
