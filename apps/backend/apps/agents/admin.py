from django.contrib import admin

from apps.agents.models import AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun


@admin.register(AgentDefinition)
class AgentDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'agent_type', 'is_enabled', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    list_filter = ('agent_type', 'is_enabled')


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'agent_definition', 'status', 'triggered_from', 'started_at', 'finished_at')
    list_filter = ('status', 'triggered_from', 'agent_definition__slug')
    search_fields = ('summary', 'agent_definition__slug')


@admin.register(AgentPipelineRun)
class AgentPipelineRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'pipeline_type', 'status', 'triggered_from', 'started_at', 'finished_at')
    list_filter = ('pipeline_type', 'status', 'triggered_from')
    search_fields = ('summary',)


@admin.register(AgentHandoff)
class AgentHandoffAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_agent_run', 'to_agent_definition', 'handoff_type', 'created_at')
    list_filter = ('handoff_type', 'to_agent_definition__slug')
    search_fields = ('payload_summary',)
