from __future__ import annotations

from typing import Any

from django.conf import settings


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _choose_source(payload: dict[str, Any]) -> dict[str, Any]:
    latest = payload.get('latest_llm_shadow_summary')
    if isinstance(latest, dict) and latest:
        return dict(latest)
    shadow = payload.get('llm_shadow_summary')
    if isinstance(shadow, dict) and shadow:
        return dict(shadow)
    return {}


def build_llm_aux_signal_summary(*, payload: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(getattr(settings, 'OLLAMA_AUX_SIGNAL_ENABLED', False))
    source = _choose_source(payload)
    source_artifact_id = source.get('artifact_id')

    summary = {
        'enabled': enabled,
        'source_artifact_id': source_artifact_id,
        'aux_signal_status': 'DISABLED' if not enabled else 'UNAVAILABLE',
        'aux_signal_recommendation': 'observe',
        'aux_signal_reason_codes': ['LLM_AUX_SIGNAL_DISABLED'] if not enabled else ['LLM_AUX_SIGNAL_SOURCE_MISSING'],
        'aux_signal_weight': 0.0,
        'advisory_only': True,
        'affects_execution': False,
        'paper_only': True,
        'real_read_only': True,
    }
    if not enabled:
        return summary

    reasoning_status = str(source.get('llm_shadow_reasoning_status') or 'UNAVAILABLE').upper()
    recommendation_mode = str(source.get('recommendation_mode') or 'observe').lower()
    confidence = str(source.get('confidence') or 'low').lower()
    stance = str(source.get('stance') or 'unclear').lower()
    advisory_only = _as_bool(source.get('advisory_only'), default=True)
    shadow_only = _as_bool(source.get('shadow_only'), default=True)

    if not source:
        return summary
    if reasoning_status != 'OK':
        summary.update(
            {
                'aux_signal_status': 'UNAVAILABLE',
                'aux_signal_reason_codes': ['LLM_AUX_SIGNAL_REASONING_NOT_OK'],
                'aux_signal_recommendation': 'observe',
            }
        )
        return summary
    if not (advisory_only and shadow_only):
        summary.update(
            {
                'aux_signal_status': 'UNAVAILABLE',
                'aux_signal_reason_codes': ['LLM_AUX_SIGNAL_CONTRACT_MISMATCH'],
                'aux_signal_recommendation': 'observe',
            }
        )
        return summary

    reason_codes: list[str] = ['LLM_AUX_SIGNAL_FROM_PERSISTED_SHADOW_ARTIFACT']
    if source_artifact_id is not None:
        reason_codes.append('LLM_AUX_SIGNAL_ARTIFACT_LINKED')

    if recommendation_mode == 'worth_review' and confidence in {'high', 'medium'} and stance in {'bullish', 'bearish'}:
        summary.update(
            {
                'aux_signal_status': 'REVIEW_PRIORITIZED',
                'aux_signal_recommendation': 'prioritize_human_review',
                'aux_signal_reason_codes': reason_codes + ['LLM_AUX_SIGNAL_WORTH_REVIEW'],
                'aux_signal_weight': 0.8 if confidence == 'high' else 0.6,
            }
        )
        return summary

    if recommendation_mode == 'caution' and confidence in {'high', 'medium'}:
        summary.update(
            {
                'aux_signal_status': 'ATTENTION_HINT',
                'aux_signal_recommendation': 'raise_attention_hint',
                'aux_signal_reason_codes': reason_codes + ['LLM_AUX_SIGNAL_CAUTION_HINT'],
                'aux_signal_weight': 0.5 if confidence == 'high' else 0.35,
            }
        )
        return summary

    summary.update(
        {
            'aux_signal_status': 'MONITOR',
            'aux_signal_recommendation': 'observe',
            'aux_signal_reason_codes': reason_codes + ['LLM_AUX_SIGNAL_MONITOR_ONLY'],
            'aux_signal_weight': 0.2 if confidence == 'high' else 0.1,
        }
    )
    return summary
