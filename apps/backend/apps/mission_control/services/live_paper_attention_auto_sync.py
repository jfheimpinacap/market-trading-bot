from __future__ import annotations

from typing import Any


def run_live_paper_attention_auto_sync() -> dict[str, Any]:
    from apps.mission_control.services.live_paper_attention_bridge import sync_live_paper_attention_alert

    try:
        payload = sync_live_paper_attention_alert()
    except Exception as exc:
        return {
            'attempted': True,
            'success': False,
            'alert_action': 'ERROR',
            'attention_mode': None,
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': None,
            'sync_summary': f'auto-sync failed: {exc.__class__.__name__}',
        }

    return {
        'attempted': True,
        'success': True,
        'alert_action': payload.get('alert_action'),
        'attention_mode': payload.get('attention_mode'),
        'session_active': bool(payload.get('session_active', False)),
        'heartbeat_active': bool(payload.get('heartbeat_active', False)),
        'current_session_status': payload.get('current_session_status'),
        'funnel_status': payload.get('funnel_status'),
        'stalled_stage': payload.get('stalled_stage'),
        'sync_summary': payload.get('alert_status_summary', ''),
    }
