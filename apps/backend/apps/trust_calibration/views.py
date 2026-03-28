from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRun, TrustCalibrationRunStatus
from apps.trust_calibration.serializers import (
    AutomationFeedbackSnapshotSerializer,
    TrustCalibrationRecommendationSerializer,
    TrustCalibrationRunRequestSerializer,
    TrustCalibrationRunSerializer,
)
from apps.trust_calibration.services import build_policy_tuning_candidates, build_recommendations, build_summary_payload, consolidate_feedback


class TrustCalibrationRunCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = TrustCalibrationRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        run = TrustCalibrationRun.objects.create(
            started_at=timezone.now(),
            status=TrustCalibrationRunStatus.IN_PROGRESS,
            window_days=validated.get('window_days', 30),
            source_type=validated.get('source_type', ''),
            runbook_template_slug=validated.get('runbook_template_slug', ''),
            profile_slug=validated.get('profile_slug', ''),
            include_degraded=validated.get('include_degraded', True),
            summary='Collecting approval/autopilot feedback evidence.',
            metadata={'mode': 'recommendation_only', 'manual_first': True},
        )

        snapshots = consolidate_feedback(run)
        recommendations = build_recommendations(run, snapshots)
        candidates = build_policy_tuning_candidates(recommendations)

        payload = {
            'run': TrustCalibrationRunSerializer(run).data,
            'feedback_count': len(snapshots),
            'recommendation_count': len(recommendations),
            'candidates': candidates,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class TrustCalibrationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TrustCalibrationRunSerializer

    def get_queryset(self):
        return TrustCalibrationRun.objects.order_by('-started_at', '-id')[:50]


class TrustCalibrationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TrustCalibrationRunSerializer
    queryset = TrustCalibrationRun.objects.order_by('-started_at', '-id')


class TrustCalibrationRecommendationListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TrustCalibrationRecommendationSerializer

    def get_queryset(self):
        run_id = self.request.query_params.get('run_id')
        queryset = TrustCalibrationRecommendation.objects.select_related('run', 'snapshot').order_by('-created_at', '-id')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(run_id=int(run_id))
        return queryset[:200]


class TrustCalibrationFeedbackListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutomationFeedbackSnapshotSerializer

    def get_queryset(self):
        run_id = self.request.query_params.get('run_id')
        queryset = AutomationFeedbackSnapshot.objects.select_related('run').order_by('-created_at', '-id')
        if run_id and run_id.isdigit():
            queryset = queryset.filter(run_id=int(run_id))
        return queryset[:200]


class TrustCalibrationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary_payload(), status=status.HTTP_200_OK)


class TrustCalibrationRunReportView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk, *args, **kwargs):
        run = get_object_or_404(TrustCalibrationRun, pk=pk)
        payload = {
            'run': TrustCalibrationRunSerializer(run).data,
            'feedback': AutomationFeedbackSnapshotSerializer(run.feedback_snapshots.all(), many=True).data,
            'recommendations': TrustCalibrationRecommendationSerializer(run.recommendations.all(), many=True).data,
            'policy_tuning_candidates': build_policy_tuning_candidates(list(run.recommendations.all())),
        }
        return Response(payload, status=status.HTTP_200_OK)
