from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.continuous_demo.models import ContinuousDemoSession
from apps.evaluation_lab.models import (
    CalibrationBucket,
    EffectivenessMetric,
    EvaluationRecommendation,
    EvaluationRun,
    EvaluationRuntimeRun,
    OutcomeAlignmentRecord,
)
from apps.evaluation_lab.serializers import (
    CalibrationBucketSerializer,
    EffectivenessMetricSerializer,
    EvaluationRecommendationSerializer,
    EvaluationRunSerializer,
    EvaluationRuntimeRunSerializer,
    OutcomeAlignmentRecordSerializer,
)
from apps.evaluation_lab.services import build_run_for_continuous_session, build_runtime_summary, compare_runs, run_runtime_evaluation


class EvaluationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EvaluationRunSerializer

    def get_queryset(self):
        return EvaluationRun.objects.select_related('related_continuous_session', 'related_semi_auto_run', 'metric_set').order_by('-started_at', '-id')[:50]


class EvaluationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EvaluationRunSerializer
    queryset = EvaluationRun.objects.select_related('related_continuous_session', 'related_semi_auto_run', 'metric_set').order_by('-started_at', '-id')


class EvaluationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id').first()
        recent_runs = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id')[:5]
        payload = {
            'latest_run': EvaluationRunSerializer(latest_run).data if latest_run else None,
            'recent_runs': EvaluationRunSerializer(recent_runs, many=True).data,
            'total_runs': EvaluationRun.objects.count(),
            'completed_runs': EvaluationRun.objects.filter(status='READY').count(),
        }
        return Response(payload, status=status.HTTP_200_OK)


class EvaluationRecentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        recent = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id')[:10]
        return Response(EvaluationRunSerializer(recent, many=True).data, status=status.HTTP_200_OK)


class EvaluationBuildForSessionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ContinuousDemoSession, pk=session_id)
        run = build_run_for_continuous_session(session)
        return Response(EvaluationRunSerializer(run).data, status=status.HTTP_201_CREATED)


class EvaluationComparisonView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        left_id = request.query_params.get('left_id')
        right_id = request.query_params.get('right_id')
        if not (left_id and right_id and left_id.isdigit() and right_id.isdigit()):
            return Response({'detail': 'Provide left_id and right_id query params.'}, status=status.HTTP_400_BAD_REQUEST)
        left = get_object_or_404(EvaluationRun.objects.select_related('metric_set'), pk=int(left_id))
        right = get_object_or_404(EvaluationRun.objects.select_related('metric_set'), pk=int(right_id))
        return Response(compare_runs(left, right), status=status.HTTP_200_OK)


class RuntimeEvaluationRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        run = run_runtime_evaluation()
        return Response(EvaluationRuntimeRunSerializer(run).data, status=status.HTTP_201_CREATED)


class OutcomeAlignmentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OutcomeAlignmentRecordSerializer

    def get_queryset(self):
        queryset = OutcomeAlignmentRecord.objects.select_related('run', 'linked_market', 'linked_market__provider').order_by('-created_at', '-id')
        provider = self.request.query_params.get('provider')
        category = self.request.query_params.get('category')
        model_mode = self.request.query_params.get('model_mode')
        status_filter = self.request.query_params.get('status')
        if provider:
            queryset = queryset.filter(metadata__provider=provider)
        if category:
            queryset = queryset.filter(metadata__category=category)
        if model_mode:
            queryset = queryset.filter(metadata__model_mode=model_mode)
        if status_filter:
            queryset = queryset.filter(alignment_status=status_filter)
        return queryset[:300]


class CalibrationBucketListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CalibrationBucketSerializer

    def get_queryset(self):
        queryset = CalibrationBucket.objects.select_related('run').order_by('-created_at', '-id')
        segment_scope = self.request.query_params.get('segment_scope')
        segment_value = self.request.query_params.get('segment_value')
        if segment_scope:
            queryset = queryset.filter(segment_scope=segment_scope)
        if segment_value:
            queryset = queryset.filter(segment_value=segment_value)
        return queryset[:300]


class CalibrationBucketDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = CalibrationBucketSerializer
    queryset = CalibrationBucket.objects.order_by('-created_at', '-id')


class EffectivenessMetricListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EffectivenessMetricSerializer

    def get_queryset(self):
        queryset = EffectivenessMetric.objects.select_related('run').order_by('-created_at', '-id')
        metric_scope = self.request.query_params.get('metric_scope')
        status_filter = self.request.query_params.get('status')
        if metric_scope:
            queryset = queryset.filter(metric_scope=metric_scope)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset[:300]


class EffectivenessMetricDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EffectivenessMetricSerializer
    queryset = EffectivenessMetric.objects.order_by('-created_at', '-id')


class EvaluationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = EvaluationRecommendationSerializer

    def get_queryset(self):
        return EvaluationRecommendation.objects.select_related('run', 'target_metric').order_by('-created_at', '-id')[:200]


class RuntimeEvaluationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payload = build_runtime_summary()
        latest_run = payload['latest_run']
        recommendations = payload.get('recommendations', [])
        return Response(
            {
                'latest_run': EvaluationRuntimeRunSerializer(latest_run).data if latest_run else None,
                'manual_review_required': payload['manual_review_required'],
                'poor_metric_count': payload['poor_metric_count'],
                'drift_flags': payload['drift_flags'],
                'recommendations': EvaluationRecommendationSerializer(recommendations, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
