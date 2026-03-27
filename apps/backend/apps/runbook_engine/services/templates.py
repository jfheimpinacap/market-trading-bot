from apps.runbook_engine.models import RunbookStepActionKind, RunbookTemplate

DEFAULT_TEMPLATES: list[dict] = [
    {
        'slug': 'incident_mission_control_pause',
        'name': 'Incident mission control pause',
        'trigger_type': 'incident',
        'severity_hint': 'HIGH',
        'description': 'Guide for critical incidents that require pausing mission control and triaging incident posture.',
        'metadata': {
            'steps': [
                {'step_type': 'inspect_state', 'title': 'Inspect current incident and degraded state', 'instructions': 'Review incident severity/status and degraded mode rationale.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_incident_context'},
                {'step_type': 'open_trace', 'title': 'Open related trace', 'instructions': 'Open trace for the source object to review lineage and upstream context.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_trace'},
                {'step_type': 'run_detection', 'title': 'Run incident detection', 'instructions': 'Run incident detection to refresh incident inventory.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_incident_detection'},
                {'step_type': 'pause_mission', 'title': 'Pause mission control', 'instructions': 'Pause mission control until mitigation steps complete.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'pause_mission_control'},
                {'step_type': 'confirm', 'title': 'Confirm containment', 'instructions': 'Confirm that incident blast radius is contained before resuming workflows.', 'action_kind': RunbookStepActionKind.CONFIRM, 'action_name': 'confirm_containment'},
            ]
        },
    },
    {
        'slug': 'rollout_guardrail_response',
        'name': 'Rollout guardrail response',
        'trigger_type': 'rollout_guardrail',
        'severity_hint': 'CRITICAL',
        'description': 'Respond to rollout guardrail breaches with pause/rollback and certification checks.',
        'metadata': {
            'steps': [
                {'step_type': 'inspect_rollout', 'title': 'Inspect rollout guardrail event', 'instructions': 'Confirm breach code, severity, and impacted run.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_rollout'},
                {'step_type': 'pause_rollout', 'title': 'Pause rollout run', 'instructions': 'Pause the active rollout run to stop further exposure.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'pause_rollout'},
                {'step_type': 'rollback_rollout', 'title': 'Rollback rollout', 'instructions': 'Rollback candidate routing when breach severity requires rollback.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'rollback_rollout'},
                {'step_type': 'cert_review', 'title': 'Run certification review', 'instructions': 'Re-evaluate certification envelope after breach.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_certification_review'},
            ]
        },
    },
    {
        'slug': 'certification_downgrade_review',
        'name': 'Certification downgrade review',
        'trigger_type': 'certification',
        'severity_hint': 'HIGH',
        'description': 'Review certification downgrade and required remediation steps.',
        'metadata': {
            'steps': [
                {'step_type': 'review_cert', 'title': 'Review current certification level', 'instructions': 'Inspect latest certification run and remediation constraints.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_certification'},
                {'step_type': 'run_cert', 'title': 'Run certification review', 'instructions': 'Execute a new certification review run for latest posture.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_certification_review'},
                {'step_type': 'review_queue', 'title': 'Review operator queue', 'instructions': 'Verify high-priority remediation tasks in operator queue.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_operator_queue'},
            ]
        },
    },
    {
        'slug': 'venue_parity_gap_investigation',
        'name': 'Venue parity gap investigation',
        'trigger_type': 'venue_parity',
        'severity_hint': 'HIGH',
        'description': 'Investigate execution venue parity gaps and related trace evidence.',
        'metadata': {
            'steps': [
                {'step_type': 'review_parity', 'title': 'Review venue parity gap', 'instructions': 'Inspect parity issues and mismatch summary.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_execution_venue'},
                {'step_type': 'open_trace', 'title': 'Open trace for source object', 'instructions': 'Use trace explorer for source object lineage.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_trace'},
                {'step_type': 'reconcile', 'title': 'Run venue reconciliation', 'instructions': 'Run venue account reconciliation workflow.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_venue_reconciliation'},
            ]
        },
    },
    {
        'slug': 'queue_pressure_relief',
        'name': 'Queue pressure relief',
        'trigger_type': 'operator_queue',
        'severity_hint': 'MEDIUM',
        'description': 'Triage queue pressure and clear blocked manual tasks.',
        'metadata': {
            'steps': [
                {'step_type': 'review_queue', 'title': 'Review queue pressure', 'instructions': 'Inspect pending high-priority queue items.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_operator_queue'},
                {'step_type': 'run_incident_detection', 'title': 'Run incident detection', 'instructions': 'Check if queue pressure is tied to active incidents.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_incident_detection'},
                {'step_type': 'confirm', 'title': 'Confirm queue pressure stabilized', 'instructions': 'Confirm high-priority queue backlog is reduced.', 'action_kind': RunbookStepActionKind.CONFIRM, 'action_name': 'confirm_queue_stabilized'},
            ]
        },
    },
    {
        'slug': 'bridge_validation_failure_review',
        'name': 'Bridge validation failure review',
        'trigger_type': 'bridge_validation',
        'severity_hint': 'HIGH',
        'description': 'Review broker bridge validation failures and follow-up actions.',
        'metadata': {
            'steps': [
                {'step_type': 'review_bridge', 'title': 'Inspect bridge validation failures', 'instructions': 'Review broker bridge rejects/validation errors.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_broker_bridge'},
                {'step_type': 'open_trace', 'title': 'Open related trace', 'instructions': 'Inspect trace path around failed mapping/validation.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_trace'},
                {'step_type': 'review_queue', 'title': 'Review operator queue follow-ups', 'instructions': 'Check queued tasks created by bridge failures.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_operator_queue'},
            ]
        },
    },
    {
        'slug': 'degraded_mode_recovery',
        'name': 'Degraded mode recovery',
        'trigger_type': 'degraded_mode',
        'severity_hint': 'HIGH',
        'description': 'Recover from degraded mode and validate posture before returning to normal flow.',
        'metadata': {
            'steps': [
                {'step_type': 'inspect_degraded', 'title': 'Inspect degraded mode reasons', 'instructions': 'Review degraded modules and disabled actions.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_incident_context'},
                {'step_type': 'run_detection', 'title': 'Run incident detection', 'instructions': 'Refresh incident state before attempting recovery.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_incident_detection'},
                {'step_type': 'review_cert', 'title': 'Run certification review', 'instructions': 'Verify certification envelope still supports operation.', 'action_kind': RunbookStepActionKind.API_ACTION, 'action_name': 'run_certification_review'},
                {'step_type': 'confirm_clear', 'title': 'Confirm degraded mode cleared', 'instructions': 'Confirm degraded state transitioned to normal.', 'action_kind': RunbookStepActionKind.CONFIRM, 'action_name': 'confirm_degraded_mode_cleared'},
            ]
        },
    },
    {
        'slug': 'pre_go_live_block_review',
        'name': 'Pre-go-live block review',
        'trigger_type': 'go_live_gate',
        'severity_hint': 'MEDIUM',
        'description': 'Review go-live gate preconditions and open blocking tasks (paper/sandbox only).',
        'metadata': {
            'steps': [
                {'step_type': 'review_gate', 'title': 'Review go-live gate blockers', 'instructions': 'Inspect preconditions and checklist blockers.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_go_live_gate'},
                {'step_type': 'open_queue', 'title': 'Open operator queue', 'instructions': 'Review manual approvals and pending gate tasks.', 'action_kind': RunbookStepActionKind.REVIEW, 'action_name': 'open_operator_queue'},
                {'step_type': 'confirm_blocked', 'title': 'Confirm manual-first lock remains', 'instructions': 'Confirm system remains paper/sandbox and live execution disabled.', 'action_kind': RunbookStepActionKind.CONFIRM, 'action_name': 'confirm_manual_first_lock'},
            ]
        },
    },
]


def ensure_default_templates() -> None:
    for template in DEFAULT_TEMPLATES:
        RunbookTemplate.objects.update_or_create(
            slug=template['slug'],
            defaults={
                'name': template['name'],
                'trigger_type': template['trigger_type'],
                'description': template['description'],
                'severity_hint': template['severity_hint'],
                'is_enabled': True,
                'metadata': template['metadata'],
            },
        )


def list_templates(*, enabled_only: bool = True):
    queryset = RunbookTemplate.objects.order_by('name', 'id')
    if enabled_only:
        queryset = queryset.filter(is_enabled=True)
    return queryset
