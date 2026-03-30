from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.evaluation_lab.models import EvaluationRuntimeRun
from apps.tuning_board.models import TuningImpactHypothesis, TuningProposal, TuningProposalBundle, TuningRecommendation
from apps.tuning_board.serializers import (
    TuningImpactHypothesisSerializer,
    TuningProposalBundleSerializer,
    TuningProposalSerializer,
    TuningRecommendationSerializer,
    TuningReviewRunSerializer,
    TuningRunReviewRequestSerializer,
)
from apps.tuning_board.services import build_tuning_summary, run_tuning_review


class TuningRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = TuningRunReviewRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        evaluation_run = None
        evaluation_run_id = serializer.validated_data.get('evaluation_run_id')
        if evaluation_run_id:
            evaluation_run = get_object_or_404(EvaluationRuntimeRun, pk=evaluation_run_id)
        run = run_tuning_review(evaluation_run=evaluation_run, metadata=serializer.validated_data.get('metadata') or {})
        return Response(TuningReviewRunSerializer(run).data, status=status.HTTP_201_CREATED)


class TuningProposalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TuningProposalSerializer

    def get_queryset(self):
        queryset = TuningProposal.objects.select_related('run', 'source_metric', 'source_recommendation').order_by('-created_at', '-id')
        for field in ['target_component', 'target_scope', 'priority_level', 'proposal_status']:
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset[:300]


class TuningHypothesisListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TuningImpactHypothesisSerializer

    def get_queryset(self):
        return TuningImpactHypothesis.objects.select_related('proposal', 'proposal__run').order_by('-created_at', '-id')[:300]


class TuningRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TuningRecommendationSerializer

    def get_queryset(self):
        return TuningRecommendation.objects.select_related('run', 'target_proposal').order_by('-created_at', '-id')[:300]


class TuningBundleListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TuningProposalBundleSerializer

    def get_queryset(self):
        return TuningProposalBundle.objects.prefetch_related('linked_proposals').order_by('-created_at', '-id')[:200]


class TuningSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_tuning_summary()
        latest = payload.pop('latest_run')
        return Response({'latest_run': TuningReviewRunSerializer(latest).data if latest else None, **payload}, status=status.HTTP_200_OK)
