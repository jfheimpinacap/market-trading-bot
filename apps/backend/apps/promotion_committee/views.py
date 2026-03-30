from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.promotion_committee.models import PromotionReviewRun
from apps.promotion_committee.serializers import (
    GovernedPromotionRunRequestSerializer,
    PromotionApplyRequestSerializer,
    PromotionCaseSerializer,
    PromotionDecisionRecommendationSerializer,
    PromotionEvidencePackSerializer,
    PromotionReviewCycleRunSerializer,
    PromotionReviewRequestSerializer,
    PromotionReviewRunSerializer,
)
from apps.promotion_committee.services import (
    apply_review_decision,
    build_promotion_summary,
    get_current_recommendation,
    run_governed_promotion_review,
    run_promotion_review,
)
from apps.promotion_committee.models import PromotionCase, PromotionDecisionRecommendation, PromotionEvidencePack, PromotionReviewCycleRun


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
