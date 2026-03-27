from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.runbook_engine.models import RunbookApprovalCheckpoint, RunbookAutopilotRun, RunbookInstance, RunbookInstanceStatus, RunbookStep, RunbookTemplate
from apps.runbook_engine.serializers import (
    RunbookApprovalUpdateSerializer,
    RunbookAutopilotResumeSerializer,
    RunbookAutopilotRetrySerializer,
    RunbookAutopilotRunRequestSerializer,
    RunbookAutopilotRunSerializer,
    RunbookCompleteSerializer,
    RunbookCreateSerializer,
    RunbookInstanceSerializer,
    RunbookTemplateSerializer,
)
from apps.runbook_engine.services import (
    continue_autopilot,
    create_runbook_instance,
    ensure_default_templates,
    get_autopilot_summary,
    get_runbook_summary,
    list_templates,
    recommend_runbooks,
    retry_step,
    run_autopilot,
    run_step,
)


class RunbookTemplateListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunbookTemplateSerializer

    def get_queryset(self):
        ensure_default_templates()
        return list_templates(enabled_only=False)


class RunbookListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunbookInstanceSerializer

    def get_queryset(self):
        queryset = RunbookInstance.objects.select_related('template').prefetch_related('steps__action_results').order_by('-updated_at', '-id')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset[:100]


class RunbookDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunbookInstanceSerializer
    queryset = RunbookInstance.objects.select_related('template').prefetch_related('steps__action_results').order_by('-updated_at', '-id')


class RunbookCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        ensure_default_templates()
        serializer = RunbookCreateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        template = get_object_or_404(RunbookTemplate, slug=serializer.validated_data['template_slug'], is_enabled=True)
        instance = create_runbook_instance(
            template=template,
            source_object_type=serializer.validated_data['source_object_type'],
            source_object_id=serializer.validated_data['source_object_id'],
            priority=serializer.validated_data.get('priority', 'MEDIUM'),
            summary=serializer.validated_data.get('summary', ''),
            metadata=serializer.validated_data.get('metadata', {}),
        )
        return Response(RunbookInstanceSerializer(instance).data, status=status.HTTP_201_CREATED)


class RunbookRunStepView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, step_id, *args, **kwargs):
        instance = get_object_or_404(RunbookInstance.objects.select_related('template').prefetch_related('steps__action_results'), pk=pk)
        step = get_object_or_404(RunbookStep, pk=step_id)
        step = run_step(instance=instance, step=step)
        return Response({'step': step_id, 'status': step.status, 'runbook': RunbookInstanceSerializer(instance).data}, status=status.HTTP_200_OK)


class RunbookCompleteView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        instance = get_object_or_404(RunbookInstance, pk=pk)
        serializer = RunbookCompleteSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        note = serializer.validated_data.get('note', '')

        instance.status = RunbookInstanceStatus.COMPLETED
        metadata = instance.metadata or {}
        metadata['completion_note'] = note
        instance.metadata = metadata
        instance.save(update_fields=['status', 'metadata', 'updated_at'])

        return Response(RunbookInstanceSerializer(instance).data, status=status.HTTP_200_OK)


class RunbookSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_runbook_summary(), status=status.HTTP_200_OK)


class RunbookRecommendationsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ensure_default_templates()
        source_type = request.query_params.get('source_object_type')
        source_id = request.query_params.get('source_object_id')
        recommendations = recommend_runbooks(source_object_type=source_type, source_object_id=source_id)
        return Response({'results': recommendations}, status=status.HTTP_200_OK)


class RunbookAutopilotRunStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        instance = get_object_or_404(RunbookInstance, pk=pk)
        serializer = RunbookAutopilotRunRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        autopilot_run = run_autopilot(instance=instance, metadata=serializer.validated_data.get('metadata', {}))
        return Response(RunbookAutopilotRunSerializer(autopilot_run).data, status=status.HTTP_201_CREATED)


class RunbookAutopilotRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunbookAutopilotRunSerializer

    def get_queryset(self):
        return RunbookAutopilotRun.objects.select_related('runbook_instance').prefetch_related('step_results__runbook_step', 'approval_checkpoints').order_by('-created_at', '-id')[:100]


class RunbookAutopilotRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RunbookAutopilotRunSerializer
    queryset = RunbookAutopilotRun.objects.select_related('runbook_instance').prefetch_related('step_results__runbook_step', 'approval_checkpoints').order_by('-created_at', '-id')


class RunbookAutopilotResumeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        run = get_object_or_404(RunbookAutopilotRun, pk=pk)
        serializer = RunbookAutopilotResumeSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        checkpoint = None
        checkpoint_id = serializer.validated_data.get('checkpoint_id')
        if checkpoint_id:
            checkpoint = get_object_or_404(RunbookApprovalCheckpoint, pk=checkpoint_id, autopilot_run=run)
        else:
            checkpoint = run.approval_checkpoints.filter(status='PENDING').order_by('-created_at').first()

        resumed = continue_autopilot(
            autopilot_run=run,
            checkpoint=checkpoint,
            approved=serializer.validated_data.get('approved', True),
            reviewer=serializer.validated_data.get('reviewer', ''),
        )
        return Response(RunbookAutopilotRunSerializer(resumed).data, status=status.HTTP_200_OK)


class RunbookAutopilotRetryStepView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, step_id, *args, **kwargs):
        run = get_object_or_404(RunbookAutopilotRun, pk=pk)
        step = get_object_or_404(RunbookStep, pk=step_id, runbook_instance=run.runbook_instance)
        serializer = RunbookAutopilotRetrySerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        resumed = retry_step(autopilot_run=run, step=step, reason=serializer.validated_data.get('reason', ''))
        return Response(RunbookAutopilotRunSerializer(resumed).data, status=status.HTTP_200_OK)


class RunbookAutopilotSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_autopilot_summary(), status=status.HTTP_200_OK)


class RunbookApprovalCheckpointUpdateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        checkpoint = get_object_or_404(RunbookApprovalCheckpoint, pk=pk)
        serializer = RunbookApprovalUpdateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = continue_autopilot(
            autopilot_run=checkpoint.autopilot_run,
            checkpoint=checkpoint,
            approved=serializer.validated_data.get('approved', True),
            reviewer=serializer.validated_data.get('reviewer', ''),
        )
        return Response(RunbookAutopilotRunSerializer(run).data, status=status.HTTP_200_OK)
