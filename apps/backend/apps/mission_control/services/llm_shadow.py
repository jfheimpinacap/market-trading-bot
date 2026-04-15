from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.errors import LlmConfigurationError, LlmResponseParseError, LlmUnavailableError
from apps.llm_local.config import get_llm_local_settings
from apps.markets.models import Market

_ALLOWED_STANCES = {'bullish', 'bearish', 'unclear'}
_ALLOWED_CONFIDENCE = {'low', 'medium', 'high'}
_ALLOWED_RECOMMENDATION_MODE = {'observe', 'caution', 'worth_review'}


@dataclass(frozen=True)
class ShadowFocusCase:
    source: str
    details: dict[str, Any]


def _safe_decimal(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, (int, float, str)):
        return str(value)
    return None


def _pick_focus_case(*, funnel: dict[str, Any]) -> ShadowFocusCase | None:
    candidates: list[tuple[str, list[dict[str, Any]]]] = [
        ('prediction_risk_examples', list(funnel.get('prediction_risk_examples') or [])),
        ('prediction_intake_examples', list(funnel.get('prediction_intake_examples') or [])),
        ('handoff_scoring_examples', list(funnel.get('handoff_scoring_examples') or [])),
        ('shortlist_handoff_examples', list((funnel.get('shortlist_handoff_summary') or {}).get('shortlist_handoff_examples') or [])),
        ('market_link_examples', list(funnel.get('market_link_examples') or [])),
    ]
    for source, rows in candidates:
        for row in rows:
            if isinstance(row, dict):
                return ShadowFocusCase(source=source, details=dict(row))
    return None


def _resolve_market_context(*, focus_details: dict[str, Any]) -> dict[str, Any]:
    market_id = focus_details.get('market_id') or focus_details.get('chosen_market_id')
    market_id_int = None
    try:
        market_id_int = int(market_id) if market_id is not None else None
    except (TypeError, ValueError):
        market_id_int = None

    if market_id_int is None:
        return {'market_id': None, 'market_title': None, 'market_probability': None}

    market = Market.objects.filter(id=market_id_int).first()
    if not market:
        return {'market_id': market_id_int, 'market_title': None, 'market_probability': None}

    return {
        'market_id': market.id,
        'market_title': market.title,
        'market_probability': _safe_decimal(getattr(market, 'current_market_probability', None)),
    }


def _build_prompt_context(*, payload: dict[str, Any], funnel: dict[str, Any], focus_case: ShadowFocusCase | None) -> dict[str, Any]:
    focus = focus_case.details if focus_case else {}
    market_context = _resolve_market_context(focus_details=focus)
    return {
        'mode_contract': {
            'shadow_only': True,
            'advisory_only': True,
            'non_blocking': True,
            'paper_only': True,
            'real_read_only': True,
            'must_not_execute_trades': True,
            'must_not_change_pipeline_decisions': True,
        },
        'focus_case_source': focus_case.source if focus_case else 'none',
        'focus_case': focus,
        'market_context': market_context,
        'funnel_context': {
            'funnel_status': funnel.get('funnel_status'),
            'top_stage': funnel.get('top_stage'),
            'stalled_stage': funnel.get('stalled_stage'),
            'stalled_reason_code': funnel.get('stalled_reason_code'),
            'handoff_reason_codes': list(funnel.get('handoff_reason_codes') or []),
            'handoff_summary': funnel.get('handoff_summary'),
            'prediction_intake_summary': dict(funnel.get('prediction_intake_summary') or {}),
            'prediction_risk_summary': dict(funnel.get('prediction_risk_summary') or {}),
            'prediction_risk_caution_summary': dict(funnel.get('prediction_risk_caution_summary') or {}),
            'prediction_status_summary': dict(funnel.get('prediction_status_summary') or {}),
            'position_exposure_summary': dict(funnel.get('position_exposure_summary') or {}),
            'cash_pressure_summary': dict(funnel.get('cash_pressure_summary') or {}),
            'paper_trade_final_summary': dict(payload.get('paper_trade_final_summary') or {}),
        },
        'pipeline_status': {
            'validation_status': payload.get('validation_status'),
            'trial_status': payload.get('trial_status'),
            'trend_status': payload.get('trend_status'),
            'readiness_status': payload.get('readiness_status'),
            'gate_status': payload.get('gate_status'),
            'reason_codes': list(payload.get('reason_codes') or []),
        },
    }


def _fallback_summary(*, model: str, provider: str, status: str, message: str) -> dict[str, Any]:
    return {
        'provider': provider,
        'model': model,
        'shadow_only': True,
        'advisory_only': True,
        'non_blocking': True,
        'llm_shadow_reasoning_status': status,
        'stance': 'unclear',
        'confidence': 'low',
        'summary': message,
        'key_risks': [],
        'key_supporting_points': [],
        'recommendation_mode': 'observe',
    }


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item or '').strip()
        if text:
            normalized.append(text)
        if len(normalized) >= 4:
            break
    return normalized


def _normalize_shadow_payload(*, model: str, provider: str, response: dict[str, Any]) -> dict[str, Any]:
    stance = str(response.get('stance') or 'unclear').strip().lower()
    confidence = str(response.get('confidence') or 'low').strip().lower()
    recommendation_mode = str(response.get('recommendation_mode') or 'observe').strip().lower()
    reasoning_status = str(response.get('llm_shadow_reasoning_status') or 'OK').strip().upper()

    if stance not in _ALLOWED_STANCES:
        stance = 'unclear'
    if confidence not in _ALLOWED_CONFIDENCE:
        confidence = 'low'
    if recommendation_mode not in _ALLOWED_RECOMMENDATION_MODE:
        recommendation_mode = 'observe'
    if reasoning_status not in {'OK', 'DEGRADED', 'UNAVAILABLE'}:
        reasoning_status = 'DEGRADED'

    summary = str(response.get('summary') or '').strip()[:600]
    if not summary:
        summary = 'No structured LLM summary was produced.'

    return {
        'provider': provider,
        'model': model,
        'shadow_only': True,
        'advisory_only': True,
        'non_blocking': True,
        'llm_shadow_reasoning_status': reasoning_status,
        'stance': stance,
        'confidence': confidence,
        'summary': summary,
        'key_risks': _normalize_list(response.get('key_risks')),
        'key_supporting_points': _normalize_list(response.get('key_supporting_points')),
        'recommendation_mode': recommendation_mode,
    }


def build_llm_shadow_summary(*, payload: dict[str, Any], funnel: dict[str, Any]) -> dict[str, Any]:
    config = get_llm_local_settings()
    enabled = bool(getattr(config, 'enabled', False))
    provider = str(getattr(config, 'provider', 'ollama') or 'ollama')
    model = str(getattr(config, 'chat_model', '') or 'unknown')

    if not enabled:
        return _fallback_summary(
            model=model,
            provider=provider,
            status='UNAVAILABLE',
            message='LLM shadow analysis is disabled by configuration (OLLAMA_ENABLED/LLM_ENABLED=false).',
        )

    focus_case = _pick_focus_case(funnel=funnel)
    context_payload = _build_prompt_context(payload=payload, funnel=funnel, focus_case=focus_case)
    system_prompt = (
        'You are an auxiliary shadow analyst for a paper-only trading pipeline. '
        'Do not propose execution actions. Return compact JSON only.'
    )
    user_prompt = (
        'Analyze the provided real pipeline context in strict shadow mode. '\
        'Output JSON fields: stance, confidence, summary, key_risks, key_supporting_points, '\
        'recommendation_mode, llm_shadow_reasoning_status. '\
        f'Context: {context_payload}'
    )

    try:
        client = OllamaChatClient()
        response = client.chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint='LlmShadowSummary',
        )
        normalized = _normalize_shadow_payload(model=model, provider=provider, response=response)
        normalized['focus_case_source'] = context_payload.get('focus_case_source')
        normalized['focus_market_id'] = (context_payload.get('market_context') or {}).get('market_id')
        return normalized
    except (LlmUnavailableError, LlmConfigurationError) as exc:
        return _fallback_summary(model=model, provider=provider, status='UNAVAILABLE', message=str(exc))
    except LlmResponseParseError as exc:
        return _fallback_summary(model=model, provider=provider, status='DEGRADED', message=str(exc))
    except Exception as exc:  # pragma: no cover
        return _fallback_summary(model=model, provider=provider, status='DEGRADED', message=f'Ollama shadow analysis failed: {exc}')
