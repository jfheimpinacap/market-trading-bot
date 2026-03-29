from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_launch.models import LaunchAuthorization, LaunchReadinessSnapshot, LaunchRecommendation, LaunchRun
from apps.autonomy_launch.serializers import (
    LaunchActionSerializer,
    LaunchAuthorizationSerializer,
    LaunchReadinessSnapshotSerializer,
    LaunchRecommendationSerializer,
    LaunchRunPreflightSerializer,
    LaunchRunSerializer,
)
from apps.autonomy_launch.services import authorize_campaign, hold_campaign, list_launch_candidates, run_preflight
from apps.autonomy_scheduler.serializers import CampaignAdmissionSerializer


class AutonomyLaunchCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = list_launch_candidates()
        return Response(CampaignAdmissionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyLaunchRunPreflightView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LaunchRunPreflightSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_preflight(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': LaunchRunSerializer(result['run']).data,
                'readiness': LaunchReadinessSnapshotSerializer(result['snapshots'], many=True).data,
                'recommendations': LaunchRecommendationSerializer(result['recommendations'], many=True).data,
                'candidates': CampaignAdmissionSerializer(result['candidates'], many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AutonomyLaunchReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = LaunchReadinessSnapshot.objects.select_related('campaign').order_by('-created_at', '-id')[:100]
        return Response(LaunchReadinessSnapshotSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyLaunchRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = LaunchRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:100]
        return Response(LaunchRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyLaunchAuthorizationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = LaunchAuthorization.objects.select_related('campaign', 'approved_request').order_by('-created_at', '-id')[:100]
        return Response(LaunchAuthorizationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyLaunchSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = LaunchRun.objects.select_related('active_window').order_by('-created_at', '-id').first()
        latest_recommendation = LaunchRecommendation.objects.order_by('-created_at', '-id').first()
        latest_auth = LaunchAuthorization.objects.order_by('-created_at', '-id').first()
        return Response(
            {
                'latest_run_id': latest_run.id if latest_run else None,
                'program_posture': latest_run.program_posture if latest_run else None,
                'active_window_id': latest_run.active_window_id if latest_run else None,
                'candidate_count': latest_run.candidate_count if latest_run else 0,
                'ready_count': latest_run.ready_count if latest_run else 0,
                'waiting_count': latest_run.waiting_count if latest_run else 0,
                'blocked_count': latest_run.blocked_count if latest_run else 0,
                'approval_required_count': latest_run.approval_required_count if latest_run else 0,
                'latest_recommendation_type': latest_recommendation.recommendation_type if latest_recommendation else None,
                'latest_authorization_status': latest_auth.authorization_status if latest_auth else None,
            },
            status=status.HTTP_200_OK,
        )


class AutonomyLaunchAuthorizeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = LaunchActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        row = authorize_campaign(campaign_id=campaign_id, actor=serializer.validated_data['actor'])
        return Response(LaunchAuthorizationSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyLaunchHoldView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = LaunchActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        row = hold_campaign(
            campaign_id=campaign_id,
            actor=serializer.validated_data['actor'],
            rationale=serializer.validated_data.get('rationale') or 'Manual operator hold',
        )
        return Response(LaunchAuthorizationSerializer(row).data, status=status.HTTP_200_OK)
