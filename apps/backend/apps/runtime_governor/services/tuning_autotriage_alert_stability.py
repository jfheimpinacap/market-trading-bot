from __future__ import annotations

from typing import Any

from apps.operator_alerts.models import OperatorAlert
from apps.runtime_governor.services.tuning_autotriage import MODE_REVIEW_NOW

MATERIAL_SIGNAL_FIELDS = (
    'human_attention_mode',
    'alert_needed',
    'alert_severity',
    'next_recommended_scope',
    'next_recommended_reason_codes',
    'requires_human_now',
)


def normalize_reason_codes(raw_codes: Any) -> list[str]:
    if not isinstance(raw_codes, list):
        return []
    normalized = [str(code).strip() for code in raw_codes if str(code).strip()]
    return sorted(set(normalized))


def build_material_signal(*, digest: dict[str, Any], mode: str, alert_needed: bool, alert_severity: str | None) -> dict[str, Any]:
    return {
        'human_attention_mode': mode,
        'alert_needed': bool(alert_needed),
        'alert_severity': alert_severity,
        'next_recommended_scope': digest.get('next_recommended_scope'),
        'next_recommended_reason_codes': normalize_reason_codes(digest.get('next_recommended_reason_codes')),
        'requires_human_now': bool(digest.get('requires_human_now', mode == MODE_REVIEW_NOW)),
    }


def build_existing_material_signal(alert: OperatorAlert) -> dict[str, Any]:
    metadata = alert.metadata or {}
    mode = metadata.get('human_attention_mode')
    return {
        'human_attention_mode': mode,
        'alert_needed': bool(metadata.get('alert_needed', True)),
        'alert_severity': alert.severity,
        'next_recommended_scope': metadata.get('next_recommended_scope'),
        'next_recommended_reason_codes': normalize_reason_codes(metadata.get('next_recommended_reason_codes')),
        'requires_human_now': bool(metadata.get('requires_human_now', mode == MODE_REVIEW_NOW)),
    }


def detect_material_change(*, previous_signal: dict[str, Any], current_signal: dict[str, Any]) -> list[str]:
    changed_fields: list[str] = []
    for field in MATERIAL_SIGNAL_FIELDS:
        if previous_signal.get(field) != current_signal.get(field):
            changed_fields.append(field)
    return changed_fields
