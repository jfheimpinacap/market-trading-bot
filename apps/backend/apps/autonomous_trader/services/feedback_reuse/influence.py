from __future__ import annotations

from decimal import Decimal

from apps.autonomous_trader.models import (
    AutonomousCandidateStatus,
    AutonomousFeedbackCandidateContext,
    AutonomousFeedbackInfluenceRecord,
    AutonomousFeedbackInfluenceStatus,
    AutonomousFeedbackInfluenceType,
    AutonomousTradeCandidate,
)


def apply_feedback_influence(*, candidate: AutonomousTradeCandidate, context: AutonomousFeedbackCandidateContext) -> AutonomousFeedbackInfluenceRecord:
    pre_confidence = candidate.confidence
    reason_codes: list[str] = []
    influence_type = AutonomousFeedbackInfluenceType.CONTEXT_ONLY
    influence_status = AutonomousFeedbackInfluenceStatus.SUGGESTED
    summary = 'Context attached without direct adjustment.'

    failure_modes = context.top_failure_modes or []
    has_repeat_loss_pattern = any('loss' in str(mode).lower() or 'repeat' in str(mode).lower() for mode in failure_modes)

    if context.retrieval_status == 'BLOCKED':
        influence_status = AutonomousFeedbackInfluenceStatus.BLOCKED
        reason_codes.append('MEMORY_RETRIEVAL_BLOCKED')
        summary = 'Could not retrieve memory context; candidate unchanged to preserve guardrails.'
    elif context.retrieval_status == 'NO_HITS':
        reason_codes.append('NO_RELEVANT_LEARNING_FOUND')
        influence_type = AutonomousFeedbackInfluenceType.CONTEXT_ONLY
        influence_status = AutonomousFeedbackInfluenceStatus.SKIPPED
        summary = 'No relevant memory hits; candidate kept unchanged.'
    elif has_repeat_loss_pattern and context.top_precedent_count >= 2:
        influence_type = AutonomousFeedbackInfluenceType.BLOCK_REPEAT_PATTERN
        influence_status = AutonomousFeedbackInfluenceStatus.APPLIED
        reason_codes.extend(['REPEAT_LOSS_PATTERN', 'CONSERVATIVE_BLOCK'])
        candidate.candidate_status = AutonomousCandidateStatus.BLOCKED
        candidate.risk_posture = 'BLOCKED_BY_FEEDBACK_REUSE'
        summary = 'Repeated adverse precedent pattern found; candidate conservatively blocked.'
    elif context.top_precedent_count >= 1:
        influence_type = AutonomousFeedbackInfluenceType.CONFIDENCE_REDUCTION
        influence_status = AutonomousFeedbackInfluenceStatus.APPLIED
        reason_codes.extend(['ADVERSE_PRECEDENT', 'CONFIDENCE_REDUCTION'])
        candidate.confidence = max(Decimal('0.0000'), candidate.confidence - Decimal('0.0800'))
        candidate.metadata = {
            **(candidate.metadata or {}),
            'feedback_reuse': {
                'caution_boost': True,
                'confidence_delta': '-0.0800',
                'reason_codes': reason_codes,
            },
        }
        summary = 'Adverse precedents triggered conservative confidence reduction and caution boost.'

    candidate.save(update_fields=['candidate_status', 'risk_posture', 'confidence', 'metadata', 'updated_at'])

    return AutonomousFeedbackInfluenceRecord.objects.create(
        linked_candidate_context=context,
        linked_candidate=candidate,
        influence_type=influence_type,
        influence_status=influence_status,
        influence_reason_codes=reason_codes,
        influence_summary=summary,
        pre_adjust_confidence=pre_confidence,
        post_adjust_confidence=candidate.confidence,
        metadata={
            'paper_only': True,
            'bounded_influence': True,
            'risk_policy_authority_unchanged': True,
        },
    )
