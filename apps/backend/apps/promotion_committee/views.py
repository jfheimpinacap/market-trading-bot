from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.promotion_committee.models import PromotionReviewRun
from apps.promotion_committee.serializers import (
    PromotionApplyRequestSerializer,
    PromotionReviewRequestSerializer,
    PromotionReviewRunSerializer,
)
from apps.promotion_committee.services import apply_review_decision, build_promotion_summary, get_current_recommendation, run_promotion_review


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
