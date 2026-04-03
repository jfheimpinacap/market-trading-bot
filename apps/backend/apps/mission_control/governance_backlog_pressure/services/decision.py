from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceBacklogPressureDecisionType,
    GovernanceBacklogPressureSnapshot,
)


@dataclass
class BacklogPressureDecisionPayload:
    decision_type: str
    decision_summary: str
    reason_codes: list[str]
    metadata: dict


def build_backlog_pressure_decision(*, snapshot: GovernanceBacklogPressureSnapshot) -> BacklogPressureDecisionPayload:
    state = snapshot.governance_backlog_pressure_state
    if state == 'HIGH':
        return BacklogPressureDecisionPayload(
            decision_type=GovernanceBacklogPressureDecisionType.SET_HIGH_PRESSURE,
            decision_summary='Backlog pressure is high; runtime posture should adopt conservative guardrails.',
            reason_codes=[*snapshot.reason_codes, 'RUNTIME_CONSERVATIVE_SIGNAL'],
            metadata={'target_runtime_posture': 'CAUTION', 'allow_new_activity': False},
        )
    if state == 'CAUTION':
        return BacklogPressureDecisionPayload(
            decision_type=GovernanceBacklogPressureDecisionType.SET_CAUTION_PRESSURE,
            decision_summary='Backlog pressure is cautionary; runtime should prefer conservative execution cadence.',
            reason_codes=[*snapshot.reason_codes, 'RUNTIME_CAUTIOUS_SIGNAL'],
            metadata={'target_runtime_posture': 'CAUTION', 'allow_new_activity': True},
        )
    return BacklogPressureDecisionPayload(
        decision_type=GovernanceBacklogPressureDecisionType.KEEP_NORMAL_PRESSURE,
        decision_summary='Backlog pressure is within expected bounds; keep normal posture signal.',
        reason_codes=[*snapshot.reason_codes, 'RUNTIME_BASELINE_SIGNAL'],
        metadata={'target_runtime_posture': 'NORMAL', 'allow_new_activity': True},
    )
