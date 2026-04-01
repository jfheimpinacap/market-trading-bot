from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mission_control.models import (
    AutonomousMissionCycleExecution,
    AutonomousMissionCycleOutcome,
    AutonomousMissionCyclePlan,
    AutonomousMissionRuntimeRecommendation,
    AutonomousMissionRuntimeRun,
    MissionControlCycle,
    MissionControlSession,
)
from apps.mission_control.serializers import (
    AutonomousCycleExecutionSerializer,
    AutonomousCycleOutcomeSerializer,
    AutonomousCyclePlanSerializer,
    AutonomousRuntimeRecommendationSerializer,
    AutonomousRuntimeRunRequestSerializer,
    AutonomousRuntimeRunSerializer,
    MissionControlCycleSerializer,
    MissionControlSessionSerializer,
    MissionControlStartSerializer,
)
from apps.mission_control.services import pause_session, resume_session, run_cycle_now, start_session, status_snapshot, stop_session
from apps.mission_control.services.autonomous_runtime import build_autonomous_runtime_summary, run_autonomous_runtime


class MissionControlStatusView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(status_snapshot(), status=status.HTTP_200_OK)


class MissionControlStartView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = MissionControlStartSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        profile_slug = payload.pop('profile_slug', None)
        session = start_session(profile_slug=profile_slug, overrides=payload)
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlPauseView(APIView):
    def post(self, request, *args, **kwargs):
        session = pause_session()
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlResumeView(APIView):
    def post(self, request, *args, **kwargs):
        session = resume_session()
        return Response(MissionControlSessionSerializer(session).data, status=status.HTTP_200_OK)


class MissionControlStopView(APIView):
    def post(self, request, *args, **kwargs):
        session = stop_session()
        return Response(MissionControlSessionSerializer(session).data if session else {'status': 'STOPPED'}, status=status.HTTP_200_OK)


class MissionControlRunCycleView(APIView):
    def post(self, request, *args, **kwargs):
        cycle = run_cycle_now(profile_slug=request.data.get('profile_slug'))
        return Response(MissionControlCycleSerializer(cycle).data, status=status.HTTP_200_OK)


class MissionControlSessionListView(generics.ListAPIView):
    serializer_class = MissionControlSessionSerializer

    def get_queryset(self):
        return MissionControlSession.objects.order_by('-started_at', '-id')[:50]


class MissionControlSessionDetailView(generics.RetrieveAPIView):
    serializer_class = MissionControlSessionSerializer
    queryset = MissionControlSession.objects.order_by('-started_at', '-id')


class MissionControlCycleListView(generics.ListAPIView):
    serializer_class = MissionControlCycleSerializer

    def get_queryset(self):
        return MissionControlCycle.objects.select_related('session').prefetch_related('steps').order_by('-started_at', '-id')[:80]


class MissionControlCycleDetailView(generics.RetrieveAPIView):
    serializer_class = MissionControlCycleSerializer
    queryset = MissionControlCycle.objects.select_related('session').prefetch_related('steps').order_by('-started_at', '-id')


class MissionControlSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        latest_session = MissionControlSession.objects.order_by('-started_at').first()
        latest_cycle = MissionControlCycle.objects.order_by('-started_at').first()
        return Response({
            'latest_session': MissionControlSessionSerializer(latest_session).data if latest_session else None,
            'latest_cycle': MissionControlCycleSerializer(latest_cycle).data if latest_cycle else None,
            'session_count': MissionControlSession.objects.count(),
            'cycle_count': MissionControlCycle.objects.count(),
        }, status=status.HTTP_200_OK)


class RunAutonomousRuntimeView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AutonomousRuntimeRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        runtime_run = run_autonomous_runtime(**serializer.validated_data)
        return Response(AutonomousRuntimeRunSerializer(runtime_run).data, status=status.HTTP_200_OK)


class AutonomousRuntimeRunListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeRunSerializer
    queryset = AutonomousMissionRuntimeRun.objects.order_by('-started_at', '-id')[:50]


class AutonomousCyclePlanListView(generics.ListAPIView):
    serializer_class = AutonomousCyclePlanSerializer
    queryset = AutonomousMissionCyclePlan.objects.select_related('linked_runtime_run').order_by('-created_at', '-id')[:100]


class AutonomousCycleExecutionListView(generics.ListAPIView):
    serializer_class = AutonomousCycleExecutionSerializer
    queryset = AutonomousMissionCycleExecution.objects.select_related('linked_cycle_plan').order_by('-created_at', '-id')[:100]


class AutonomousCycleOutcomeListView(generics.ListAPIView):
    serializer_class = AutonomousCycleOutcomeSerializer
    queryset = AutonomousMissionCycleOutcome.objects.select_related('linked_cycle_execution').order_by('-created_at', '-id')[:100]


class AutonomousRuntimeRecommendationListView(generics.ListAPIView):
    serializer_class = AutonomousRuntimeRecommendationSerializer
    queryset = AutonomousMissionRuntimeRecommendation.objects.order_by('-created_at', '-id')[:100]


class AutonomousRuntimeSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        return Response(build_autonomous_runtime_summary(), status=status.HTTP_200_OK)
