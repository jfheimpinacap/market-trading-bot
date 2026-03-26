from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.models import AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun
from apps.agents.serializers import (
    AgentDefinitionSerializer,
    AgentHandoffSerializer,
    AgentPipelineRunSerializer,
    AgentRunSerializer,
    RunPipelineSerializer,
)
from apps.agents.services import ensure_default_agent_definitions, run_agent_pipeline


class AgentDefinitionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentDefinitionSerializer

    def get_queryset(self):
        ensure_default_agent_definitions()
        return AgentDefinition.objects.order_by('name')


class AgentRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentRunSerializer

    def get_queryset(self):
        queryset = AgentRun.objects.select_related('agent_definition', 'pipeline_run').order_by('-started_at', '-id')
        pipeline_run = self.request.query_params.get('pipeline_run')
        if pipeline_run:
            queryset = queryset.filter(pipeline_run_id=pipeline_run)
        return queryset[:200]


class AgentRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentRunSerializer
    queryset = AgentRun.objects.select_related('agent_definition', 'pipeline_run').order_by('-started_at', '-id')


class AgentPipelineRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentPipelineRunSerializer

    def get_queryset(self):
        return AgentPipelineRun.objects.order_by('-started_at', '-id')[:200]


class AgentPipelineRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentPipelineRunSerializer
    queryset = AgentPipelineRun.objects.order_by('-started_at', '-id')


class AgentHandoffListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = AgentHandoffSerializer

    def get_queryset(self):
        queryset = AgentHandoff.objects.select_related('from_agent_run__agent_definition', 'to_agent_definition').order_by('-created_at', '-id')
        pipeline_run = self.request.query_params.get('pipeline_run')
        if pipeline_run:
            queryset = queryset.filter(pipeline_run_id=pipeline_run)
        return queryset[:200]


class AgentRunPipelineView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RunPipelineSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = run_agent_pipeline(
            pipeline_type=serializer.validated_data['pipeline_type'],
            triggered_from=serializer.validated_data.get('triggered_from', 'manual'),
            payload=serializer.validated_data.get('payload') or {},
        )
        return Response(AgentPipelineRunSerializer(run).data, status=status.HTTP_200_OK)


class AgentSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ensure_default_agent_definitions()
        agents = AgentDefinition.objects.all()
        payload = {
            'total_agents': agents.count(),
            'enabled_agents': agents.filter(is_enabled=True).count(),
            'total_runs': AgentRun.objects.count(),
            'total_handoffs': AgentHandoff.objects.count(),
            'total_pipeline_runs': AgentPipelineRun.objects.count(),
            'latest_pipeline_run': AgentPipelineRunSerializer(AgentPipelineRun.objects.order_by('-started_at', '-id').first()).data
            if AgentPipelineRun.objects.exists()
            else None,
            'latest_agent_run': AgentRunSerializer(AgentRun.objects.select_related('agent_definition').order_by('-started_at', '-id').first()).data
            if AgentRun.objects.exists()
            else None,
        }
        data = payload
        data['runs_by_status'] = {item['status']: item['total'] for item in AgentRun.objects.values('status').annotate(total=Count('id'))}
        data['pipelines_by_type'] = {
            item['pipeline_type']: item['total'] for item in AgentPipelineRun.objects.values('pipeline_type').annotate(total=Count('id'))
        }
        return Response(data, status=status.HTTP_200_OK)
