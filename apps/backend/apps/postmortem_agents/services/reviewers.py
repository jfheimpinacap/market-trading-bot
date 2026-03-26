from __future__ import annotations

from decimal import Decimal

from apps.llm_local.clients import OllamaChatClient
from apps.llm_local.errors import LlmUnavailableError
from apps.postmortem_agents.models import PostmortemPerspectiveType, PostmortemReviewStatus
from apps.postmortem_agents.services.context import PostmortemBoardContext


def _safe_confidence(value: str | Decimal) -> Decimal:
    parsed = Decimal(str(value))
    return max(Decimal('0.0000'), min(Decimal('1.0000'), parsed)).quantize(Decimal('0.0001'))


def _llm_structured_review(*, perspective: str, evidence: dict, fallback: dict) -> dict:
    prompt = (
        'Return JSON with keys: conclusion (string), key_findings (object), confidence (0-1 number), '
        'recommended_actions (array of short strings). Use only supplied evidence. '
        f'Perspective: {perspective}. Evidence: {evidence}'
    )
    try:
        payload = OllamaChatClient().chat_json(
            system_prompt='You are a strict postmortem reviewer. Never invent facts. Respond only in compact JSON.',
            user_prompt=prompt,
            schema_hint='PostmortemPerspectiveReview',
        )
        return {
            'status': PostmortemReviewStatus.SUCCESS,
            'conclusion': str(payload.get('conclusion', fallback['conclusion']))[:1000],
            'key_findings': payload.get('key_findings') or fallback['key_findings'],
            'confidence': _safe_confidence(payload.get('confidence', fallback['confidence'])),
            'recommended_actions': payload.get('recommended_actions') or fallback['recommended_actions'],
            'metadata': {'llm_used': True},
        }
    except (LlmUnavailableError, Exception) as exc:  # graceful fallback
        return {
            'status': PostmortemReviewStatus.PARTIAL,
            'conclusion': fallback['conclusion'],
            'key_findings': fallback['key_findings'],
            'confidence': fallback['confidence'],
            'recommended_actions': fallback['recommended_actions'],
            'metadata': {'llm_used': False, 'llm_error': str(exc)},
        }


def run_narrative_review(context: PostmortemBoardContext) -> dict:
    candidate = context.research_candidate
    relation = candidate.relation if candidate else 'unknown'
    fallback = {
        'conclusion': f'Narrative review suggests relation={relation} versus market odds.',
        'key_findings': {
            'relation': relation,
            'short_thesis': candidate.short_thesis if candidate else '',
            'narrative_pressure': str(candidate.narrative_pressure) if candidate else '0',
            'review_outcome': context.review.outcome,
        },
        'confidence': Decimal('0.6300') if candidate else Decimal('0.3500'),
        'recommended_actions': [
            'Require stronger narrative evidence when divergence is high.',
            'Track weak-signal trades as low-conviction setups.',
        ],
    }
    evidence = fallback['key_findings']
    return _llm_structured_review(perspective=PostmortemPerspectiveType.NARRATIVE, evidence=evidence, fallback=fallback)


def run_prediction_review(context: PostmortemBoardContext) -> dict:
    score = context.prediction_score
    fallback = {
        'conclusion': 'Prediction review indicates edge quality and calibration should be rechecked.',
        'key_findings': {
            'system_probability': str(score.system_probability) if score else None,
            'market_probability': str(score.market_probability) if score else None,
            'edge': str(score.edge) if score else None,
            'confidence': str(score.confidence) if score else None,
            'review_outcome': context.review.outcome,
        },
        'confidence': Decimal('0.7000') if score else Decimal('0.3000'),
        'recommended_actions': [
            'Downweight low-edge setups with weak confidence bands.',
            'Audit calibration drift for similar markets.',
        ],
    }
    return _llm_structured_review(
        perspective=PostmortemPerspectiveType.PREDICTION,
        evidence=fallback['key_findings'],
        fallback=fallback,
    )


def run_risk_review(context: PostmortemBoardContext) -> dict:
    assessment = context.risk_assessment
    sizing = context.risk_sizing
    fallback = {
        'conclusion': 'Risk review highlights whether sizing and guardrails matched realized downside.',
        'key_findings': {
            'risk_level': assessment.risk_level if assessment else None,
            'risk_score': str(assessment.risk_score) if assessment and assessment.risk_score is not None else None,
            'adjusted_quantity': str(sizing.adjusted_quantity) if sizing else None,
            'base_quantity': str(sizing.base_quantity) if sizing else None,
            'review_pnl_estimate': str(context.review.pnl_estimate),
        },
        'confidence': Decimal('0.7600') if assessment else Decimal('0.3300'),
        'recommended_actions': [
            'Tighten sizing when risk score is elevated and narrative is weak.',
            'Escalate trades with repeated unfavorable postmortems.',
        ],
    }
    return _llm_structured_review(perspective=PostmortemPerspectiveType.RISK, evidence=fallback['key_findings'], fallback=fallback)


def run_runtime_review(context: PostmortemBoardContext) -> dict:
    fallback = {
        'conclusion': 'Runtime/safety review captures whether operational mode and safety friction influenced execution quality.',
        'key_findings': {
            'runtime_mode': context.runtime_state.current_mode if context.runtime_state else None,
            'runtime_status': context.runtime_state.status if context.runtime_state else None,
            'safety_events_count': len(context.safety_events),
            'operator_queue_count': len(context.operator_items),
            'watch_events_count': len(context.watch_events),
        },
        'confidence': Decimal('0.6500'),
        'recommended_actions': [
            'Escalate similar conditions to operator queue earlier when safety events appear.',
            'Correlate runtime transitions with trade quality for governance tuning.',
        ],
    }
    return _llm_structured_review(perspective=PostmortemPerspectiveType.RUNTIME, evidence=fallback['key_findings'], fallback=fallback)


def run_learning_review(context: PostmortemBoardContext, perspective_reviews: list[dict]) -> dict:
    fallback = {
        'conclusion': 'Learning synthesis consolidated board evidence into actionable and auditable notes.',
        'key_findings': {
            'perspectives_reviewed': [item['perspective_type'] for item in perspective_reviews],
            'active_learning_adjustments': len(context.recent_learning_adjustments),
            'review_outcome': context.review.outcome,
        },
        'confidence': Decimal('0.7200'),
        'recommended_actions': [
            'Create enriched learning note with primary failure mode and trade scope.',
            'Rebuild learning memory when severe recurring patterns are present.',
        ],
    }
    return _llm_structured_review(perspective=PostmortemPerspectiveType.LEARNING, evidence=fallback['key_findings'], fallback=fallback)
