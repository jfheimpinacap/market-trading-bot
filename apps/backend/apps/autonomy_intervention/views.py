from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_intervention.models import CampaignInterventionAction, CampaignInterventionRequest
from apps.autonomy_intervention.serializers import (
    CampaignInterventionActionSerializer,
    CampaignInterventionRequestSerializer,
    CreateInterventionRequestSerializer,
    ExecuteInterventionRequestSerializer,
    RunInterventionReviewSerializer,
)
from apps.autonomy_intervention.services import build_intervention_summary, create_request, execute_request, run_intervention_review


class AutonomyInterventionRequestsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignInterventionRequest.objects.select_related('campaign', 'approval_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignInterventionRequestSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyInterventionRequestDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, request_id: int, *args, **kwargs):
        row = get_object_or_404(CampaignInterventionRequest.objects.select_related('campaign', 'approval_request'), pk=request_id)
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyInterventionActionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignInterventionAction.objects.select_related('campaign', 'intervention_request').order_by('-created_at', '-id')[:200]
        return Response(CampaignInterventionActionSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyInterventionSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_intervention_summary(), status=status.HTTP_200_OK)


class AutonomyInterventionRunReviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunInterventionReviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_intervention_review(actor=serializer.validated_data.get('actor') or 'operator-ui')
        return Response(
            {
                'run_id': result['run'].id,
                'created_request_count': len(result['created_requests']),
                'created_request_ids': [row.id for row in result['created_requests']],
            },
            status=status.HTTP_200_OK,
        )


class AutonomyInterventionCreateRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, campaign_id: int, *args, **kwargs):
        serializer = CreateInterventionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(AutonomyCampaign, pk=campaign_id)
        row = create_request(campaign=campaign, **serializer.validated_data)
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class AutonomyInterventionExecuteRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, request_id: int, *args, **kwargs):
        serializer = ExecuteInterventionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        row = get_object_or_404(CampaignInterventionRequest, pk=request_id)
        action = execute_request(
            request=row,
            actor=serializer.validated_data.get('actor') or 'operator-ui',
            rationale=serializer.validated_data.get('rationale') or 'Manual intervention execution',
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(CampaignInterventionActionSerializer(action).data, status=status.HTTP_200_OK)


class AutonomyInterventionCancelRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, request_id: int, *args, **kwargs):
        row = get_object_or_404(CampaignInterventionRequest, pk=request_id)
        if row.request_status not in {'OPEN', 'READY', 'APPROVAL_REQUIRED', 'BLOCKED'}:
            return Response({'detail': 'Request cannot be cancelled in current state.'}, status=status.HTTP_400_BAD_REQUEST)
        row.request_status = 'EXPIRED'
        row.save(update_fields=['request_status', 'updated_at'])
        return Response(CampaignInterventionRequestSerializer(row).data, status=status.HTTP_200_OK)
