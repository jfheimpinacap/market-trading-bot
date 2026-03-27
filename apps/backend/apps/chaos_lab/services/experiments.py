from apps.chaos_lab.models import ChaosExperiment

DEFAULT_EXPERIMENTS = [
    {
        'name': 'Provider sync stale/degraded',
        'slug': 'provider-sync-failure',
        'experiment_type': 'provider_sync_failure',
        'severity': 'high',
        'target_module': 'real_data_sync',
        'description': 'Inject a failed/stale provider sync run and validate stale-data detection + mitigation.',
        'config': {'provider': 'kalshi', 'stale_hours': 3},
    },
    {
        'name': 'LLM unavailable fallback',
        'slug': 'llm-unavailable',
        'experiment_type': 'llm_unavailable',
        'severity': 'warning',
        'target_module': 'llm_local',
        'description': 'Inject synthetic LLM unreachable signal to validate conservative degraded behavior.',
        'config': {'mode': 'synthetic_incident_seed'},
    },
    {
        'name': 'Mission control repeated failures',
        'slug': 'mission-control-step-failure',
        'experiment_type': 'mission_control_step_failure',
        'severity': 'critical',
        'target_module': 'mission_control',
        'description': 'Inject repeated failed mission cycles to trigger incident commander pause/degraded actions.',
        'config': {'failed_cycles': 4},
    },
    {
        'name': 'Rollout critical guardrail trigger',
        'slug': 'rollout-guardrail-trigger',
        'experiment_type': 'rollout_guardrail_trigger',
        'severity': 'critical',
        'target_module': 'rollout_manager',
        'description': 'Inject a critical rollout guardrail event and verify rollback orchestration.',
        'config': {'guardrail_code': 'EXECUTION_DRAG_SPIKE'},
    },
    {
        'name': 'Queue pressure spike',
        'slug': 'queue-pressure-spike',
        'experiment_type': 'queue_pressure_spike',
        'severity': 'high',
        'target_module': 'operator_queue',
        'description': 'Inject pending queue backlog to validate queue-pressure detection and mitigation.',
        'config': {'pending_items': 22},
    },
    {
        'name': 'Notification delivery failure',
        'slug': 'notification-delivery-failure',
        'experiment_type': 'notification_delivery_failure',
        'severity': 'high',
        'target_module': 'notification_center',
        'description': 'Inject repeated failed deliveries and validate notification incident path.',
        'config': {'failed_deliveries': 6},
    },
    {
        'name': 'Execution no-fill anomaly',
        'slug': 'execution-fill-anomaly',
        'experiment_type': 'execution_fill_anomaly',
        'severity': 'high',
        'target_module': 'execution_simulator',
        'description': 'Inject no-fill execution attempts to validate anomaly detection.',
        'config': {'failed_attempts': 13},
    },
]


def ensure_default_experiments() -> dict:
    created = 0
    updated = 0
    for payload in DEFAULT_EXPERIMENTS:
        _, is_created = ChaosExperiment.objects.update_or_create(
            slug=payload['slug'],
            defaults=payload,
        )
        created += int(is_created)
        updated += int(not is_created)
    return {'created': created, 'updated': updated, 'total': ChaosExperiment.objects.count()}
