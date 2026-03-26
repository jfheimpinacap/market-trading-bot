from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.agents.models import AgentDefinition, AgentPipelineRun, AgentRun, AgentStatus, AgentTriggeredFrom
from apps.agents.services.pipelines import PipelineExecutionError, execute_pipeline
from apps.agents.services.registry import ensure_default_agent_definitions


@dataclass
class OrchestrationContext:
    pipeline_run: AgentPipelineRun
    triggered_from: str
    agents_by_slug: dict[str, AgentDefinition]
    agent_runs_count: int = 0
    handoffs_count: int = 0

    def start_agent_run(self, *, agent: AgentDefinition) -> AgentRun:
        run = AgentRun.objects.create(
            agent_definition=agent,
            pipeline_run=self.pipeline_run,
            status=AgentStatus.RUNNING,
            triggered_from=self.triggered_from,
            started_at=timezone.now(),
            details={},
        )
        self.agent_runs_count += 1
        return run

    def finish_agent_run(self, run: AgentRun, *, status: str, summary: str, details: dict) -> None:
        run.status = status
        run.finished_at = timezone.now()
        run.summary = summary
        run.details = details
        run.save(update_fields=['status', 'finished_at', 'summary', 'details', 'updated_at'])


@transaction.atomic
def run_agent_pipeline(*, pipeline_type: str, triggered_from: str = AgentTriggeredFrom.MANUAL, payload: dict | None = None) -> AgentPipelineRun:
    payload = payload or {}
    definitions = ensure_default_agent_definitions()
    agents_by_slug = {item.slug: item for item in definitions}

    pipeline_run = AgentPipelineRun.objects.create(
        pipeline_type=pipeline_type,
        status=AgentStatus.RUNNING,
        triggered_from=triggered_from,
        started_at=timezone.now(),
        details={'requested_payload': payload},
    )
    context = OrchestrationContext(
        pipeline_run=pipeline_run,
        triggered_from=triggered_from,
        agents_by_slug=agents_by_slug,
    )

    try:
        result = execute_pipeline(context=context, pipeline_type=pipeline_type, payload=payload)
        pipeline_run.status = result.status
        pipeline_run.summary = result.summary
        pipeline_run.details = {**pipeline_run.details, **result.details}
        pipeline_run.agents_run_count = result.agent_runs_count
        pipeline_run.handoffs_count = result.handoffs_count
    except PipelineExecutionError as exc:
        pipeline_run.status = AgentStatus.FAILED
        pipeline_run.summary = f'Pipeline failed: {exc}'
        pipeline_run.details = {**pipeline_run.details, 'error': str(exc)}
    except Exception as exc:
        pipeline_run.status = AgentStatus.FAILED
        pipeline_run.summary = f'Pipeline crashed: {exc}'
        pipeline_run.details = {**pipeline_run.details, 'error': str(exc)}

    pipeline_run.finished_at = timezone.now()
    pipeline_run.save(
        update_fields=[
            'status',
            'summary',
            'details',
            'agents_run_count',
            'handoffs_count',
            'finished_at',
            'updated_at',
        ]
    )
    return pipeline_run
