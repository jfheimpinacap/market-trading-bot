from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_campaign.serializers import (
    AutonomyCampaignSerializer,
    CampaignActionSerializer,
    CreateAutonomyCampaignSerializer,
)
from apps.autonomy_campaign.services import abort_campaign, advance_campaign, build_summary_payload, create_campaign, list_campaigns_queryset, start_campaign


class CreateAutonomyCampaignView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CreateAutonomyCampaignSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        campaign = create_campaign(
            source_type=payload['source_type'],
            source_object_id=payload['source_object_id'],
            title=payload.get('title') or f"Autonomy campaign from {payload['source_type']} #{payload['source_object_id']}",
            summary=payload.get('summary') or 'Staged autonomy transition program generated from recommendation source.',
            metadata=payload.get('metadata') or {},
        )
        return Response(AutonomyCampaignSerializer(campaign).data, status=status.HTTP_201_CREATED)


class AutonomyCampaignListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AutonomyCampaignSerializer

    def get_queryset(self):
        return list_campaigns_queryset()[:50]


class AutonomyCampaignDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk: int, *args, **kwargs):
        campaign = get_object_or_404(list_campaigns_queryset(), pk=pk)
        return Response(AutonomyCampaignSerializer(campaign).data, status=status.HTTP_200_OK)


class StartAutonomyCampaignView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = CampaignActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(list_campaigns_queryset(), pk=pk)
        updated = start_campaign(campaign=campaign, actor=serializer.validated_data.get('actor') or 'operator-ui')
        return Response(AutonomyCampaignSerializer(updated).data, status=status.HTTP_200_OK)


class ResumeAutonomyCampaignView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = CampaignActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(list_campaigns_queryset(), pk=pk)
        updated = advance_campaign(campaign=campaign, actor=serializer.validated_data.get('actor') or 'operator-ui')
        return Response(AutonomyCampaignSerializer(updated).data, status=status.HTTP_200_OK)


class AbortAutonomyCampaignView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = CampaignActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        campaign = get_object_or_404(list_campaigns_queryset(), pk=pk)
        updated = abort_campaign(campaign=campaign, reason=serializer.validated_data.get('reason') or '', actor=serializer.validated_data.get('actor') or 'operator-ui')
        return Response(AutonomyCampaignSerializer(updated).data, status=status.HTTP_200_OK)


class AutonomyCampaignSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary_payload(), status=status.HTTP_200_OK)
