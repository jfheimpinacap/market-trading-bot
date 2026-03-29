from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_activation.models import ActivationRecommendation, ActivationRun, CampaignActivation
from apps.autonomy_activation.serializers import (
    ActivationCandidateSerializer,
    ActivationDispatchSerializer,
    ActivationRecommendationSerializer,
    ActivationRunDispatchReviewSerializer,
    ActivationRunSerializer,
    CampaignActivationSerializer,
)
from apps.autonomy_activation.services import dispatch_campaign, run_dispatch_review
from apps.autonomy_activation.services.candidates import build_activation_candidates
from apps.autonomy_campaign.models import AutonomyCampaign


class AutonomyActivationCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(ActivationCandidateSerializer(build_activation_candidates(), many=True).data, status=status.HTTP_200_OK)


class AutonomyActivationRunDispatchReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ActivationRunDispatchReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_dispatch_review(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': ActivationRunSerializer(result['run']).data,
                'candidates': ActivationCandidateSerializer(result['candidates'], many=True).data,
                'recommendations': ActivationRecommendationSerializer(result['recommendations'], many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AutonomyActivationRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = ActivationRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:100]
        return Response(ActivationRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyActivationActivationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignActivation.objects.select_related('campaign', 'launch_authorization').order_by('-created_at', '-id')[:100]
        return Response(CampaignActivationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyActivationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = ActivationRun.objects.select_related('active_window').order_by('-created_at', '-id').first()
        recent = CampaignActivation.objects.order_by('-created_at', '-id')[:50]
        return Response(
            {
                'latest_run_id': latest_run.id if latest_run else None,
                'current_program_posture': latest_run.current_program_posture if latest_run else None,
                'active_window_id': latest_run.active_window_id if latest_run else None,
                'active_window_name': latest_run.active_window.name if latest_run and latest_run.active_window else None,
                'candidate_count': latest_run.candidate_count if latest_run else 0,
                'ready_count': latest_run.ready_count if latest_run else 0,
                'blocked_count': latest_run.blocked_count if latest_run else 0,
                'expired_count': latest_run.expired_count if latest_run else 0,
                'dispatch_started_count': sum(1 for row in recent if row.activation_status == 'STARTED'),
                'failed_count': sum(1 for row in recent if row.activation_status == 'FAILED'),
                'recent_activations': len(recent),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyActivationDispatchView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = ActivationDispatchSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = AutonomyCampaign.objects.get(pk=campaign_id)
        activation = dispatch_campaign(
            campaign=campaign,
            actor=serializer.validated_data['actor'],
            trigger_source=serializer.validated_data['trigger_source'],
            rationale=serializer.validated_data['rationale'],
        )
        return Response(CampaignActivationSerializer(activation).data, status=status.HTTP_200_OK)
