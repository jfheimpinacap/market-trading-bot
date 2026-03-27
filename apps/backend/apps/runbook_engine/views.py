from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.runbook_engine.models import RunbookInstance, RunbookInstanceStatus, RunbookStep, RunbookTemplate
from apps.runbook_engine.serializers import RunbookCompleteSerializer, RunbookCreateSerializer, RunbookInstanceSerializer, RunbookTemplateSerializer
from apps.runbook_engine.services import create_runbook_instance, ensure_default_templates, get_runbook_summary, list_templates, recommend_runbooks, run_step


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
