from django.utils import timezone

from apps.certification_board.services.review import run_certification_review
from apps.incident_commander.services import run_detection
from apps.mission_control.services.controller import pause_session
from apps.rollout_manager.models import StackRolloutRun, StackRolloutRunStatus
from apps.rollout_manager.services.plans import pause_rollout_run
from apps.rollout_manager.services.rollback import rollback_run
from apps.runbook_engine.models import RunbookActionResult, RunbookActionStatus, RunbookStep
from apps.trace_explorer.services.query import run_trace_query
from apps.venue_account.services.reconciliation import run_reconciliation


def _completed_result(*, step: RunbookStep, action_name: str, summary: str, status: str, output_refs: dict | None = None, metadata: dict | None = None):
    now = timezone.now()
    return RunbookActionResult.objects.create(
        runbook_step=step,
        action_name=action_name,
        action_status=status,
        started_at=now,
        finished_at=now,
        result_summary=summary,
        output_refs=output_refs or {},
        metadata=metadata or {},
    )


def execute_step_action(*, step: RunbookStep) -> RunbookActionResult:
    action_name = (step.metadata or {}).get('action_name', step.step_type)
    action_kind = step.action_kind
    source_type = step.runbook_instance.source_object_type
    source_id = step.runbook_instance.source_object_id

    try:
        if action_kind in {'manual', 'review', 'confirm'}:
            refs = {}
            if action_name == 'open_trace' and source_type and source_id:
                refs = {'trace_url': f'/trace?root_type={source_type}&root_id={source_id}'}
            return _completed_result(
                step=step,
                action_name=action_name,
                status=RunbookActionStatus.SUCCESS,
                summary='Manual/review step recorded. No automatic remediation executed.',
                output_refs=refs,
                metadata={'manual_first': True},
            )

        if action_name == 'run_incident_detection':
            result = run_detection()
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Incident detection completed.', output_refs=result)

        if action_name == 'pause_mission_control':
            session = pause_session()
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Mission control paused.', output_refs={'session_id': session.id, 'status': session.status})

        if action_name == 'run_certification_review':
            run = run_certification_review(metadata={'trigger': 'runbook_engine'})
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Certification review completed.', output_refs={'certification_run_id': run.id, 'certification_level': run.certification_level})

        if action_name == 'pause_rollout':
            run = StackRolloutRun.objects.filter(status=StackRolloutRunStatus.RUNNING).order_by('-created_at').first()
            if not run:
                return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SKIPPED, summary='No active rollout run available to pause.')
            paused = pause_rollout_run(run=run)
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Rollout paused.', output_refs={'run_id': paused.id, 'status': paused.status})

        if action_name == 'rollback_rollout':
            run = StackRolloutRun.objects.filter(status__in=[StackRolloutRunStatus.RUNNING, StackRolloutRunStatus.PAUSED]).order_by('-created_at').first()
            if not run:
                return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SKIPPED, summary='No rollout run available to rollback.')
            rolled_back = rollback_run(run=run, reason='Runbook guardrail response', actor='runbook_engine')
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Rollout rolled back.', output_refs={'run_id': rolled_back.id, 'status': rolled_back.status})

        if action_name == 'run_venue_reconciliation':
            rec = run_reconciliation(metadata={'trigger': 'runbook_engine'})
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Venue reconciliation completed.', output_refs={'reconciliation_id': rec.id, 'mismatches_count': rec.mismatches_count})

        if action_name == 'open_trace':
            trace = run_trace_query(root_type=source_type, root_id=source_id)
            query_run = trace.get('query_run')
            return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SUCCESS, summary='Trace query executed.', output_refs={'query_run_id': query_run.id if query_run else None, 'partial': trace.get('partial', True)})

        return _completed_result(step=step, action_name=action_name, status=RunbookActionStatus.SKIPPED, summary='No mapped API action; step recorded for manual execution.')
    except Exception as exc:
        return _completed_result(
            step=step,
            action_name=action_name,
            status=RunbookActionStatus.FAILED,
            summary='Step action failed.',
            metadata={'error': str(exc)},
        )
