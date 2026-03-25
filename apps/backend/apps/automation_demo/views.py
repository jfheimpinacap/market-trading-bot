from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automation_demo.models import DemoAutomationRun
from apps.automation_demo.serializers import (
    DemoAutomationActionRequestSerializer,
    DemoAutomationRunSerializer,
    DemoAutomationSummarySerializer,
)
from apps.automation_demo.services import execute_demo_action, get_automation_summary, run_demo_cycle, run_full_learning_cycle


class DemoAutomationActionView(APIView):
    authentication_classes = []
    permission_classes = []
    action_type: str | None = None

    def post(self, request, *args, **kwargs):
        serializer = DemoAutomationActionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        triggered_from = serializer.validated_data['triggered_from']
        run = execute_demo_action(action_type=self.action_type, triggered_from=triggered_from)
        return Response(DemoAutomationRunSerializer(run).data)


class SimulateTickView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.SIMULATE_TICK


class GenerateSignalsView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.GENERATE_SIGNALS


class RevaluePortfolioView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.REVALUE_PORTFOLIO


class GenerateTradeReviewsView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.GENERATE_TRADE_REVIEWS


class SyncDemoStateView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.SYNC_DEMO_STATE


class RebuildLearningMemoryView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.REBUILD_LEARNING_MEMORY


class SyncRealDataView(DemoAutomationActionView):
    action_type = DemoAutomationRun.ActionType.SYNC_REAL_DATA


class RunDemoCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = DemoAutomationActionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_demo_cycle(triggered_from=serializer.validated_data['triggered_from'])
        return Response(DemoAutomationRunSerializer(run).data)


class RunFullLearningCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = DemoAutomationActionRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_full_learning_cycle(triggered_from=serializer.validated_data['triggered_from'])
        return Response(DemoAutomationRunSerializer(run).data)


class DemoAutomationRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = DemoAutomationRunSerializer

    def get_queryset(self):
        limit_param = self.request.query_params.get('limit')
        queryset = DemoAutomationRun.objects.order_by('-started_at', '-id')
        if limit_param and limit_param.isdigit():
            return queryset[: int(limit_param)]
        return queryset[:25]


class DemoAutomationRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = DemoAutomationRunSerializer
    queryset = DemoAutomationRun.objects.order_by('-started_at', '-id')


class DemoAutomationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        summary = get_automation_summary()
        payload = {
            **summary,
            'latest_run': DemoAutomationRunSerializer(summary['latest_run']).data if summary['latest_run'] else None,
            'last_by_action': {
                key: DemoAutomationRunSerializer(value).data if value else None
                for key, value in summary['last_by_action'].items()
            },
        }
        serializer = DemoAutomationSummarySerializer(payload)
        return Response(serializer.data)
