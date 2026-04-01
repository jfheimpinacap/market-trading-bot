from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autonomous_trader.models import (
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)
from apps.autonomous_trader.serializers import (
    AutonomousTradeCandidateSerializer,
    AutonomousTradeCycleRunSerializer,
    AutonomousTradeDecisionSerializer,
    AutonomousTradeExecutionSerializer,
    AutonomousTradeOutcomeSerializer,
    AutonomousTradeWatchRecordSerializer,
    RunCycleSerializer,
)
from apps.autonomous_trader.services import build_summary, run_autonomous_cycle


class AutonomousTradeRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_autonomous_cycle(**serializer.validated_data)
        return Response({'run': result['run'].id, 'candidate_count': len(result['candidates'])}, status=status.HTTP_200_OK)


class AutonomousTradeRunWatchCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunCycleSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data['cycle_mode'] = 'WATCH_ONLY'
        result = run_autonomous_cycle(**data)
        return Response({'run': result['run'].id, 'watch_records': len(result['watch_records'])}, status=status.HTTP_200_OK)


class AutonomousTradeCyclesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeCycleRun.objects.order_by('-started_at', '-id')[:100]
        return Response(AutonomousTradeCycleRunSerializer(rows, many=True).data)


class AutonomousTradeCycleDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, cycle_id: int, *args, **kwargs):
        row = get_object_or_404(AutonomousTradeCycleRun, pk=cycle_id)
        return Response(AutonomousTradeCycleRunSerializer(row).data)


class AutonomousTradeCandidatesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeCandidate.objects.select_related('linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeCandidateSerializer(rows, many=True).data)


class AutonomousTradeDecisionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeDecision.objects.select_related('linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeDecisionSerializer(rows, many=True).data)


class AutonomousTradeExecutionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeExecution.objects.select_related('linked_candidate__linked_market', 'linked_paper_trade').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeExecutionSerializer(rows, many=True).data)


class AutonomousTradeWatchRecordsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeWatchRecord.objects.select_related('linked_execution__linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeWatchRecordSerializer(rows, many=True).data)


class AutonomousTradeOutcomesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        rows = AutonomousTradeOutcome.objects.select_related('linked_execution__linked_candidate__linked_market').order_by('-created_at', '-id')[:200]
        return Response(AutonomousTradeOutcomeSerializer(rows, many=True).data)


class AutonomousTradeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary())
