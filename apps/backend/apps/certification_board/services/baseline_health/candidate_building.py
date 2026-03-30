from __future__ import annotations

from apps.certification_board.models import (
    ActivePaperBindingRecord,
    ActivePaperBindingStatus,
    BaselineHealthCandidate,
    BaselineHealthReadinessStatus,
    BaselineHealthRun,
)


def _build_health_inputs(binding: ActivePaperBindingRecord) -> dict:
    snapshot = binding.active_snapshot or {}
    health = snapshot.get('health') if isinstance(snapshot, dict) else {}
    if not isinstance(health, dict):
        health = {}
    return {
        'recent_calibration_signal': health.get('recent_calibration_signal'),
        'recent_risk_signal': health.get('recent_risk_signal'),
        'recent_opportunity_signal': health.get('recent_opportunity_signal'),
        'recent_drift_signal': health.get('recent_drift_signal'),
        'recent_watch_signal': health.get('recent_watch_signal'),
    }


def build_baseline_health_candidates(*, review_run: BaselineHealthRun) -> list[BaselineHealthCandidate]:
    bindings = ActivePaperBindingRecord.objects.select_related('source_activation').filter(status=ActivePaperBindingStatus.ACTIVE)

    created: list[BaselineHealthCandidate] = []
    for binding in bindings.order_by('-created_at', '-id'):
        inputs = _build_health_inputs(binding)
        blockers: list[str] = []

        missing_count = sum(1 for value in inputs.values() if value is None)
        if missing_count >= 3:
            readiness = BaselineHealthReadinessStatus.NEEDS_MORE_DATA
            blockers.append('insufficient_recent_health_inputs')
        else:
            readiness = BaselineHealthReadinessStatus.READY

        if binding.source_activation_id is None:
            blockers.append('missing_source_activation')

        if binding.target_component == '':
            readiness = BaselineHealthReadinessStatus.BLOCKED
            blockers.append('missing_target_component')

        candidate = BaselineHealthCandidate.objects.create(
            review_run=review_run,
            linked_active_binding=binding,
            linked_baseline_activation=binding.source_activation,
            target_component=binding.target_component,
            target_scope=binding.target_scope,
            active_binding_type=binding.active_binding_type,
            current_health_inputs=inputs,
            readiness_status=readiness,
            blockers=blockers,
            metadata={
                'active_binding_id': binding.id,
                'source_activation_id': binding.source_activation_id,
                'trace_chain': {
                    'paper_baseline_activation_id': binding.source_activation_id,
                    'paper_baseline_confirmation_id': getattr(binding.source_activation, 'linked_confirmation_id', None),
                },
            },
        )
        created.append(candidate)

    return created
