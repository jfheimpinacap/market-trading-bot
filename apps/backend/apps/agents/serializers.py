from rest_framework import serializers

from apps.agents.models import AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun, AgentTriggeredFrom


class AgentDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentDefinition
        fields = (
            'id',
            'name',
            'slug',
            'agent_type',
            'is_enabled',
            'description',
            'input_schema_version',
            'output_schema_version',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AgentRunSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent_definition.name', read_only=True)
    agent_slug = serializers.CharField(source='agent_definition.slug', read_only=True)

    class Meta:
        model = AgentRun
        fields = (
            'id',
            'agent_definition',
            'agent_name',
            'agent_slug',
            'pipeline_run',
            'status',
            'triggered_from',
            'started_at',
            'finished_at',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AgentPipelineRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentPipelineRun
        fields = (
            'id',
            'pipeline_type',
            'status',
            'triggered_from',
            'started_at',
            'finished_at',
            'agents_run_count',
            'handoffs_count',
            'summary',
            'details',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AgentHandoffSerializer(serializers.ModelSerializer):
    from_agent_slug = serializers.CharField(source='from_agent_run.agent_definition.slug', read_only=True)
    to_agent_slug = serializers.CharField(source='to_agent_definition.slug', read_only=True)

    class Meta:
        model = AgentHandoff
        fields = (
            'id',
            'from_agent_run',
            'from_agent_slug',
            'to_agent_definition',
            'to_agent_slug',
            'pipeline_run',
            'handoff_type',
            'payload_summary',
            'payload_ref',
            'created_at',
        )
        read_only_fields = fields


class RunPipelineSerializer(serializers.Serializer):
    pipeline_type = serializers.ChoiceField(choices=AgentPipelineRun._meta.get_field('pipeline_type').choices)
    triggered_from = serializers.ChoiceField(choices=AgentTriggeredFrom.choices, default=AgentTriggeredFrom.MANUAL, required=False)
    payload = serializers.JSONField(required=False)


class AgentSummarySerializer(serializers.Serializer):
    total_agents = serializers.IntegerField()
    enabled_agents = serializers.IntegerField()
    total_runs = serializers.IntegerField()
    total_handoffs = serializers.IntegerField()
    total_pipeline_runs = serializers.IntegerField()
    latest_pipeline_run = AgentPipelineRunSerializer(allow_null=True)
    latest_agent_run = AgentRunSerializer(allow_null=True)
