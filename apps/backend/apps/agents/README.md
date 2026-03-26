# Agents orchestration app

Agent orchestration layer for local-first, paper/demo-only workflows.

## Scope
- Agent registry (`AgentDefinition`)
- Agent runs (`AgentRun`)
- Pipeline runs (`AgentPipelineRun`)
- Agent handoffs (`AgentHandoff`)
- Controlled pipeline execution and audit-friendly outputs

## Initial pipelines
- `research_to_prediction`
- `postmortem_to_learning`
- `real_market_agent_cycle`

## Safety notes
- No real-money execution.
- No live broker execution.
- No opaque autonomous planner.
- Existing domain modules remain the source of core logic.
