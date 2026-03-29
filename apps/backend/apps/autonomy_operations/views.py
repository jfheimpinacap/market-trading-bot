from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomy_operations.models import CampaignAttentionSignal, CampaignRuntimeSnapshot, OperationsRecommendation, OperationsRun
from apps.autonomy_operations.serializers import (
    CampaignAttentionSignalSerializer,
    CampaignRuntimeSnapshotSerializer,
    OperationsRecommendationSerializer,
    RunMonitorSerializer,
    SignalActionSerializer,
)
from apps.autonomy_operations.services import acknowledge_signal, run_monitor_cycle


class AutonomyOperationsRuntimeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignRuntimeSnapshot.objects.select_related('campaign', 'current_step', 'current_checkpoint').order_by('-created_at', '-id')[:100]
        return Response(CampaignRuntimeSnapshotSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyOperationsRuntimeDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, campaign_id: int, *args, **kwargs):
        row = get_object_or_404(
            CampaignRuntimeSnapshot.objects.select_related('campaign', 'current_step', 'current_checkpoint').order_by('-created_at', '-id'),
            campaign_id=campaign_id,
        )
        return Response(CampaignRuntimeSnapshotSerializer(row).data, status=status.HTTP_200_OK)


class AutonomyOperationsRunMonitorView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunMonitorSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_monitor_cycle(actor=serializer.validated_data['actor'])
        return Response(
            {
                'run': result['run'].id,
                'runtime_count': len(result['snapshots']),
                'signal_count': len(result['signals']),
                'recommendation_count': len(result['recommendations']),
            },
            status=status.HTTP_200_OK,
        )


class AutonomyOperationsSignalsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = CampaignAttentionSignal.objects.select_related('campaign').order_by('-created_at', '-id')[:200]
        return Response(CampaignAttentionSignalSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyOperationsRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = OperationsRecommendation.objects.select_related('target_campaign').order_by('-created_at', '-id')[:200]
        return Response(OperationsRecommendationSerializer(rows, many=True).data, status=status.HTTP_200_OK)


class AutonomyOperationsSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_run = OperationsRun.objects.order_by('-created_at', '-id').first()
        open_signals = CampaignAttentionSignal.objects.filter(status='OPEN').count()
        return Response(
            {
                'latest_run_id': latest_run.id if latest_run else None,
                'active_campaign_count': latest_run.active_campaign_count if latest_run else 0,
                'on_track_count': latest_run.on_track_count if latest_run else 0,
                'caution_count': latest_run.caution_count if latest_run else 0,
                'stalled_count': latest_run.stalled_count if latest_run else 0,
                'blocked_count': latest_run.blocked_count if latest_run else 0,
                'waiting_approval_count': latest_run.waiting_approval_count if latest_run else 0,
                'observing_count': latest_run.observing_count if latest_run else 0,
                'attention_signal_count': latest_run.attention_signal_count if latest_run else 0,
                'open_attention_signal_count': open_signals,
                'recommendation_summary': latest_run.recommendation_summary if latest_run else {},
            },
            status=status.HTTP_200_OK,
        )


class AutonomyOperationsAcknowledgeSignalView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, signal_id: int, *args, **kwargs):
        serializer = SignalActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        signal = get_object_or_404(CampaignAttentionSignal, pk=signal_id)
        updated = acknowledge_signal(signal=signal, actor=serializer.validated_data['actor'])
        return Response(CampaignAttentionSignalSerializer(updated).data, status=status.HTTP_200_OK)
