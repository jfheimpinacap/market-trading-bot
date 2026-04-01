from __future__ import annotations

from decimal import Decimal

from apps.research_agent.models import PredictionHandoffStatus, ResearchPursuitScoreStatus


def build_prediction_handoff(*, assessment, score):
    reason_codes = list(assessment.reason_codes or [])

    if score.score_status == ResearchPursuitScoreStatus.READY_FOR_PREDICTION:
        handoff_status = PredictionHandoffStatus.READY
    elif score.score_status == ResearchPursuitScoreStatus.KEEP_ON_RESEARCH_WATCHLIST:
        handoff_status = PredictionHandoffStatus.WATCH
    elif score.score_status == ResearchPursuitScoreStatus.BLOCK:
        handoff_status = PredictionHandoffStatus.BLOCKED
    else:
        handoff_status = PredictionHandoffStatus.DEFERRED

    confidence = Decimal(str(score.pursuit_score))
    if handoff_status == PredictionHandoffStatus.BLOCKED:
        confidence = Decimal('0.0500')
    elif handoff_status == PredictionHandoffStatus.DEFERRED:
        confidence = min(confidence, Decimal('0.4500'))

    summary = f'{handoff_status}: generated from pursuit score {score.pursuit_score} and structural status {assessment.structural_status}'
    return handoff_status, confidence.quantize(Decimal('0.0001')), reason_codes, summary
