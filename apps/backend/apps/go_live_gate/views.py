from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.broker_bridge.models import BrokerOrderIntent
from apps.go_live_gate.models import GoLiveApprovalRequest, GoLiveChecklistRun, GoLiveRehearsalRun
from apps.go_live_gate.serializers import (
    CreateGoLiveApprovalRequestSerializer,
    GoLiveApprovalRequestSerializer,
    GoLiveChecklistRunSerializer,
    GoLiveRehearsalRunSerializer,
    RunGoLiveChecklistRequestSerializer,
    RunGoLiveRehearsalRequestSerializer,
)
from apps.go_live_gate.services import build_go_live_state, build_go_live_summary, create_approval_request, run_checklist, run_rehearsal


class GoLiveStateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_go_live_state(), status=status.HTTP_200_OK)


class GoLiveChecklistRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunGoLiveChecklistRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_checklist(
            requested_by=serializer.validated_data.get('requested_by', 'local-operator'),
            context=serializer.validated_data.get('context', 'manual'),
            manual_inputs=serializer.validated_data.get('manual_inputs') or {},
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(GoLiveChecklistRunSerializer(run).data, status=status.HTTP_201_CREATED)


class GoLiveChecklistListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GoLiveChecklistRunSerializer

    def get_queryset(self):
        return GoLiveChecklistRun.objects.order_by('-created_at', '-id')[:50]


class GoLiveApprovalCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CreateGoLiveApprovalRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        checklist_run = None
        checklist_run_id = serializer.validated_data.get('checklist_run_id')
        if checklist_run_id:
            checklist_run = GoLiveChecklistRun.objects.filter(pk=checklist_run_id).first()
        approval = create_approval_request(
            requested_by=serializer.validated_data['requested_by'],
            rationale=serializer.validated_data.get('rationale', ''),
            scope=serializer.validated_data.get('scope', 'global'),
            requested_mode=serializer.validated_data.get('requested_mode', 'PRELIVE_REHEARSAL'),
            blocking_reasons=serializer.validated_data.get('blocking_reasons') or [],
            checklist_run=checklist_run,
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(GoLiveApprovalRequestSerializer(approval).data, status=status.HTTP_201_CREATED)


class GoLiveApprovalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GoLiveApprovalRequestSerializer

    def get_queryset(self):
        return GoLiveApprovalRequest.objects.select_related('checklist_run').order_by('-created_at', '-id')[:50]


class GoLiveRehearsalRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunGoLiveRehearsalRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            intent = BrokerOrderIntent.objects.select_related('market').get(pk=serializer.validated_data['intent_id'])
        except BrokerOrderIntent.DoesNotExist:
            raise ValidationError('Intent not found.')

        run = run_rehearsal(
            intent=intent,
            requested_by=serializer.validated_data.get('requested_by', 'local-operator'),
            metadata=serializer.validated_data.get('metadata') or {},
        )
        return Response(GoLiveRehearsalRunSerializer(run).data, status=status.HTTP_201_CREATED)


class GoLiveRehearsalListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = GoLiveRehearsalRunSerializer

    def get_queryset(self):
        return GoLiveRehearsalRun.objects.select_related('intent', 'checklist_run', 'approval_request').order_by('-created_at', '-id')[:50]


class GoLiveSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_go_live_summary(), status=status.HTTP_200_OK)
