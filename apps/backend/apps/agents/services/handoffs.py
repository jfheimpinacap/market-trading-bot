from apps.agents.models import AgentDefinition, AgentHandoff, AgentPipelineRun, AgentRun


def create_handoff(
    *,
    from_agent_run: AgentRun,
    to_agent_definition: AgentDefinition,
    handoff_type: str,
    payload_summary: str,
    payload_ref: dict,
    pipeline_run: AgentPipelineRun | None = None,
) -> AgentHandoff:
    return AgentHandoff.objects.create(
        from_agent_run=from_agent_run,
        to_agent_definition=to_agent_definition,
        pipeline_run=pipeline_run,
        handoff_type=handoff_type,
        payload_summary=payload_summary,
        payload_ref=payload_ref,
    )
