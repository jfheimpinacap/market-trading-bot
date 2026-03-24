from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.continuous_demo.models import ContinuousDemoSession
from apps.evaluation_lab.models import EvaluationRun
from apps.evaluation_lab.serializers import EvaluationRunSerializer
from apps.evaluation_lab.services import build_run_for_continuous_session, compare_runs


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
