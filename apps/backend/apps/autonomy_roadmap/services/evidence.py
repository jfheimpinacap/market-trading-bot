from __future__ import annotations

from typing import Any

from apps.approval_center.services.summary import get_approval_queue_summary
from apps.autonomy_manager.models import AutonomyDomainStatus, AutonomyStageState
from apps.autonomy_rollout.models import AutonomyRolloutRun, AutonomyRolloutStatus
from apps.incident_commander.services.degraded_mode import get_current_degraded_mode_state
from apps.trust_calibration.services.reporting import build_summary_payload as build_trust_calibration_summary
from apps.certification_board.services.review import build_certification_summary


def collect_global_evidence() -> dict[str, Any]:
    states = list(AutonomyStageState.objects.select_related('domain').all().order_by('domain__slug'))
    latest_rollouts = {
        run.domain_id: run
        for run in AutonomyRolloutRun.objects.select_related('domain').order_by('domain_id', '-created_at', '-id')
    }
    degraded_state = get_current_degraded_mode_state()
    approval_summary = get_approval_queue_summary()
    trust_summary = build_trust_calibration_summary()
    certification_summary = build_certification_summary()

    domain_rows: list[dict[str, Any]] = []
    for state in states:
        rollout = latest_rollouts.get(state.domain_id)
        rollout_status = rollout.rollout_status if rollout else None
        domain_rows.append(
            {
                'domain_id': state.domain_id,
                'domain_slug': state.domain.slug,
                'current_stage': state.current_stage,
                'effective_stage': state.effective_stage,
                'status': state.status,
                'rollout_status': rollout_status,
                'under_observation': rollout_status == AutonomyRolloutStatus.OBSERVING,
                'freeze_warning': rollout_status == AutonomyRolloutStatus.FREEZE_RECOMMENDED,
                'rollback_warning': rollout_status == AutonomyRolloutStatus.ROLLBACK_RECOMMENDED,
                'is_degraded': state.status in {AutonomyDomainStatus.DEGRADED, AutonomyDomainStatus.BLOCKED},
            }
        )

    return {
        'domains': domain_rows,
        'degraded_mode': {
            'state': degraded_state.state,
            'reasons': degraded_state.reasons,
            'degraded_modules': degraded_state.degraded_modules,
        },
        'approval': approval_summary,
        'trust_calibration': trust_summary,
        'certification': {
            'latest_level': getattr(certification_summary.get('latest_run'), 'certification_level', None),
            'latest_recommendation': getattr(certification_summary.get('latest_run'), 'recommendation_code', None),
        },
    }
