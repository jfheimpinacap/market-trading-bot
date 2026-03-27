from apps.runbook_engine.models import RunbookAutopilotRun, RunbookAutopilotRunStatus, RunbookAutopilotStepOutcome


def recompute_autopilot_run_counters(*, autopilot_run: RunbookAutopilotRun) -> RunbookAutopilotRun:
    results = list(autopilot_run.step_results.all())
    autopilot_run.steps_evaluated = len(results)
    autopilot_run.steps_auto_executed = sum(1 for item in results if item.outcome == RunbookAutopilotStepOutcome.AUTO_EXECUTED)
    autopilot_run.steps_waiting_manual = sum(1 for item in results if item.outcome in [RunbookAutopilotStepOutcome.APPROVAL_REQUIRED, RunbookAutopilotStepOutcome.MANUAL_ONLY])
    autopilot_run.steps_blocked = sum(1 for item in results if item.outcome == RunbookAutopilotStepOutcome.BLOCKED)
    autopilot_run.save(update_fields=['steps_evaluated', 'steps_auto_executed', 'steps_waiting_manual', 'steps_blocked', 'updated_at'])
    return autopilot_run


def summarize_autopilot_run(*, autopilot_run: RunbookAutopilotRun) -> str:
    if autopilot_run.status == RunbookAutopilotRunStatus.COMPLETED:
        return f'Autopilot completed. Auto-executed {autopilot_run.steps_auto_executed}/{autopilot_run.steps_evaluated} evaluated steps.'
    if autopilot_run.status == RunbookAutopilotRunStatus.PAUSED_FOR_APPROVAL:
        return 'Autopilot paused for approval/manual review.'
    if autopilot_run.status == RunbookAutopilotRunStatus.BLOCKED:
        return 'Autopilot blocked by guardrail or policy constraints.'
    if autopilot_run.status == RunbookAutopilotRunStatus.FAILED:
        return 'Autopilot failed while executing a runbook step.'
    if autopilot_run.status == RunbookAutopilotRunStatus.ABORTED:
        return 'Autopilot aborted after rejected approval checkpoint.'
    return 'Autopilot running.'
