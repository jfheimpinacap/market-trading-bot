from __future__ import annotations

from typing import Any

from apps.mission_control.services.execution_exposure_diagnostics import (
    empty_execution_exposure_provenance_summary,
    empty_execution_exposure_release_audit_summary,
    normalize_execution_exposure_diagnostics,
)
from apps.mission_control.services.live_paper_autonomy_funnel import build_live_paper_autonomy_funnel_snapshot
from apps.mission_control.services.live_paper_bootstrap import PRESET_NAME


def build_execution_exposure_release_audit_snapshot(*, window_minutes: int = 60, preset_name: str | None = None) -> dict[str, Any]:
    target_preset = (preset_name or PRESET_NAME).strip() or PRESET_NAME
    funnel = build_live_paper_autonomy_funnel_snapshot(window_minutes=window_minutes, preset_name=target_preset)
    exposure_diagnostics = normalize_execution_exposure_diagnostics(
        provenance_summary=funnel.get('execution_exposure_provenance_summary'),
        provenance_examples=funnel.get('execution_exposure_provenance_examples'),
        release_audit_summary=funnel.get('execution_exposure_release_audit_summary'),
        release_audit_examples=funnel.get('execution_exposure_release_audit_examples'),
    )
    return {
        'window_minutes': int(funnel.get('window_minutes') or window_minutes),
        'preset_name': str(funnel.get('preset_name') or target_preset),
        'execution_exposure_provenance_summary': dict(
            exposure_diagnostics.get('execution_exposure_provenance_summary')
            or empty_execution_exposure_provenance_summary()
        ),
        'execution_candidate_creation_gate_summary': dict(funnel.get('execution_candidate_creation_gate_summary') or {}),
        'paper_execution_visibility_summary': str(funnel.get('paper_execution_visibility_summary') or ''),
        'execution_artifact_summary': str(funnel.get('execution_artifact_summary') or ''),
        'position_exposure_summary': dict(funnel.get('position_exposure_summary') or {}),
        'execution_exposure_release_audit_summary': dict(
            exposure_diagnostics.get('execution_exposure_release_audit_summary')
            or empty_execution_exposure_release_audit_summary()
        ),
        'execution_exposure_release_audit_examples': list(exposure_diagnostics.get('execution_exposure_release_audit_examples') or []),
    }
