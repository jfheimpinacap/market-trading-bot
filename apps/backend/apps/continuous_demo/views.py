from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession, SessionStatus
from apps.continuous_demo.serializers import (
    ContinuousDemoControlRequestSerializer,
    ContinuousDemoCycleRunSerializer,
    ContinuousDemoSessionSerializer,
)
from apps.continuous_demo.services import pause_session, resume_session, run_single_cycle, start_session, status_snapshot, stop_session


class ContinuousDemoStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = ContinuousDemoControlRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            session = start_session(settings_overrides=serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContinuousDemoSessionSerializer(session).data, status=status.HTTP_200_OK)


class ContinuousDemoStopView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        kill_switch = bool((request.data or {}).get('kill_switch', False))
        session = stop_session(kill_switch=kill_switch)
        payload = {'stopped': True, 'kill_switch': kill_switch, 'session': ContinuousDemoSessionSerializer(session).data if session else None}
        return Response(payload, status=status.HTTP_200_OK)


class ContinuousDemoPauseView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            session = pause_session()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContinuousDemoSessionSerializer(session).data, status=status.HTTP_200_OK)


class ContinuousDemoResumeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            session = resume_session()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContinuousDemoSessionSerializer(session).data, status=status.HTTP_200_OK)


class ContinuousDemoRunCycleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        session = ContinuousDemoSession.objects.filter(session_status__in=[SessionStatus.RUNNING, SessionStatus.PAUSED]).order_by('-started_at', '-id').first()
        if session is None:
            session = ContinuousDemoSession.objects.create(
                session_status=SessionStatus.RUNNING,
                summary='Manual single cycle session.',
                settings_snapshot={
                    'cycle_interval_seconds': 30,
                    'max_auto_trades_per_cycle': 2,
                    'max_auto_trades_total_per_session': 20,
                    'market_scope': 'mixed',
                    'review_after_trade': True,
                    'revalue_after_trade': True,
                },
            )
        try:
            cycle = run_single_cycle(session=session, settings=session.settings_snapshot)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ContinuousDemoCycleRunSerializer(cycle).data, status=status.HTTP_200_OK)


class ContinuousDemoStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(status_snapshot(), status=status.HTTP_200_OK)


class ContinuousDemoSessionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ContinuousDemoSessionSerializer

    def get_queryset(self):
        return ContinuousDemoSession.objects.order_by('-started_at', '-id')[:50]


class ContinuousDemoSessionDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ContinuousDemoSessionSerializer
    queryset = ContinuousDemoSession.objects.order_by('-started_at', '-id')


class ContinuousDemoCycleListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ContinuousDemoCycleRunSerializer

    def get_queryset(self):
        session_id = self.request.query_params.get('session_id')
        queryset = ContinuousDemoCycleRun.objects.select_related('session').order_by('-started_at', '-id')
        if session_id and session_id.isdigit():
            queryset = queryset.filter(session_id=int(session_id))
        return queryset[:100]


class ContinuousDemoCycleDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ContinuousDemoCycleRunSerializer
    queryset = ContinuousDemoCycleRun.objects.select_related('session').order_by('-started_at', '-id')


class ContinuousDemoSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        latest_session = ContinuousDemoSession.objects.order_by('-started_at', '-id').first()
        latest_cycle = ContinuousDemoCycleRun.objects.select_related('session').order_by('-started_at', '-id').first()
        payload = {
            'latest_session': ContinuousDemoSessionSerializer(latest_session).data if latest_session else None,
            'latest_cycle': ContinuousDemoCycleRunSerializer(latest_cycle).data if latest_cycle else None,
            'recent_failures': ContinuousDemoCycleRun.objects.filter(status='FAILED').count(),
            'recent_cycles': ContinuousDemoCycleRun.objects.count(),
        }
        return Response(payload, status=status.HTTP_200_OK)
