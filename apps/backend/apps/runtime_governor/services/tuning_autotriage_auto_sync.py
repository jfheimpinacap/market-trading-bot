from __future__ import annotations

from typing import Any

from apps.runtime_governor.services.tuning_autotriage_alert_bridge import sync_tuning_autotriage_attention_alert


def run_tuning_autotriage_attention_auto_sync() -> dict[str, Any]:
    try:
        payload = sync_tuning_autotriage_attention_alert()
    except Exception as exc:
        return {
            'attempted': True,
            'success': False,
            'alert_action': 'ERROR',
            'human_attention_mode': None,
            'next_recommended_scope': None,
            'material_change_detected': False,
            'material_change_fields': [],
            'update_suppressed': False,
            'suppression_reason': None,
            'active_alert_present': False,
            'sync_summary': f'auto-sync failed: {exc.__class__.__name__}',
        }

    return {
        'attempted': True,
        'success': True,
        'alert_action': payload.get('alert_action'),
        'human_attention_mode': payload.get('human_attention_mode'),
        'next_recommended_scope': payload.get('next_recommended_scope'),
        'material_change_detected': bool(payload.get('material_change_detected', False)),
        'material_change_fields': list(payload.get('material_change_fields', [])),
        'update_suppressed': bool(payload.get('update_suppressed', False)),
        'suppression_reason': payload.get('suppression_reason'),
        'active_alert_present': bool(payload.get('active_alert_present', False)),
        'sync_summary': payload.get('alert_status_summary', ''),
    }
