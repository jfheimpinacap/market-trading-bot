from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_scheduler.models import AdmissionRecommendation, CampaignAdmission, ChangeWindow, SchedulerRun
from apps.autonomy_scheduler.serializers import (
    AdmissionRecommendationSerializer,
    AdmitCampaignSerializer,
    CampaignAdmissionSerializer,
    ChangeWindowSerializer,
    DeferCampaignSerializer,
    SchedulerRunPlanSerializer,
    SchedulerRunSerializer,
)
from apps.autonomy_scheduler.services import admit_campaign, defer_campaign, run_scheduler_plan
from apps.autonomy_scheduler.services.queue import ensure_campaign_admissions
from apps.autonomy_scheduler.services.windows import get_active_window


class AutonomySchedulerQueueView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = ensure_campaign_admissions()
        return Response(CampaignAdmissionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySchedulerWindowsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = ChangeWindow.objects.order_by('-created_at', '-id')[:50]
        return Response(ChangeWindowSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySchedulerRunPlanView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = SchedulerRunPlanSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_scheduler_plan(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': SchedulerRunSerializer(result['run']).data,
                'recommendations': AdmissionRecommendationSerializer(result['recommendations'], many=True).data,
                'queue': CampaignAdmissionSerializer(result['queue'], many=True).data,
                'active_window': ChangeWindowSerializer(result['window']).data if result['window'] else None,
            },
            status=status.HTTP_200_OK,
        )


class AutonomySchedulerRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AdmissionRecommendation.objects.select_related('target_campaign', 'recommended_window').order_by('-created_at', '-id')[:100]
        return Response(AdmissionRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomySchedulerSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = SchedulerRun.objects.select_related('active_window').order_by('-created_at', '-id').first()
        latest_recommendation = AdmissionRecommendation.objects.order_by('-created_at', '-id').first()
        queue = ensure_campaign_admissions()
        counts = {}
        for row in queue:
            counts[row.status] = counts.get(row.status, 0) + 1
        return Response(
            {
                'latest_run_id': latest_run.id if latest_run else None,
                'current_program_posture': latest_run.current_program_posture if latest_run else None,
                'active_window_id': latest_run.active_window_id if latest_run else (get_active_window().id if get_active_window() else None),
                'max_admissible_starts': latest_run.max_admissible_starts if latest_run else 0,
                'queue_counts': counts,
                'latest_recommendation_type': latest_recommendation.recommendation_type if latest_recommendation else None,
                'latest_recommendation_campaign_id': latest_recommendation.target_campaign_id if latest_recommendation else None,
            },
            status=status.HTTP_200_OK,
        )


class AutonomySchedulerAdmitView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = AdmitCampaignSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        admission = admit_campaign(campaign_id=campaign_id, actor=serializer.validated_data['actor'])
        return Response(CampaignAdmissionSerializer(admission).data, status=status.HTTP_200_OK)


class AutonomySchedulerDeferView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = DeferCampaignSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        admission = defer_campaign(
            campaign_id=campaign_id,
            actor=serializer.validated_data['actor'],
            deferred_until=serializer.validated_data.get('deferred_until'),
            reason=serializer.validated_data.get('reason', ''),
        )
        return Response(CampaignAdmissionSerializer(admission).data, status=status.HTTP_200_OK)
