from __future__ import annotations

from apps.research_agent.models import PredictionHandoffStatus, ResearchPursuitRecommendationType


def recommendation_for_handoff(*, assessment, handoff):
    reason_codes = list(handoff.handoff_reason_codes or [])
    blockers = []

    if handoff.handoff_status == PredictionHandoffStatus.READY:
        rec_type = ResearchPursuitRecommendationType.SEND_TO_PREDICTION_IMMEDIATELY
        confidence = handoff.handoff_confidence
        rationale = 'Structural quality and pursuit score indicate prediction-ready candidate.'
    elif handoff.handoff_status == PredictionHandoffStatus.WATCH:
        if 'market_stale' in reason_codes:
            rec_type = ResearchPursuitRecommendationType.BLOCK_FOR_STALE_MARKET
            blockers = ['stale_market_activity']
        else:
            rec_type = ResearchPursuitRecommendationType.KEEP_ON_RESEARCH_WATCHLIST
        confidence = handoff.handoff_confidence
        rationale = 'Candidate remains viable but requires additional market confirmation before prediction handoff.'
    elif handoff.handoff_status == PredictionHandoffStatus.DEFERRED:
        if 'resolution_window_too_close' in reason_codes or 'resolution_window_too_far' in reason_codes:
            rec_type = ResearchPursuitRecommendationType.DEFER_FOR_POOR_TIME_WINDOW
        else:
            rec_type = ResearchPursuitRecommendationType.DEFER_FOR_LOW_LIQUIDITY
        confidence = handoff.handoff_confidence
        rationale = 'Deferred due to structural limits that can improve over time.'
    else:
        rec_type = ResearchPursuitRecommendationType.REQUIRE_MANUAL_REVIEW_FOR_STRUCTURAL_CONFLICT
        blockers = blockers + ['blocked_structural_state']
        confidence = handoff.handoff_confidence
        rationale = 'Blocked candidate requires manual review before any prediction workload allocation.'

    if assessment.linked_divergence_record and assessment.linked_divergence_record.divergence_state == 'high_divergence':
        reason_codes.append('high_divergence_signal')
        if rec_type == ResearchPursuitRecommendationType.SEND_TO_PREDICTION_IMMEDIATELY:
            rec_type = ResearchPursuitRecommendationType.PRIORITIZE_FOR_NARRATIVE_DIVERGENCE

    return rec_type, rationale, reason_codes, blockers, confidence
