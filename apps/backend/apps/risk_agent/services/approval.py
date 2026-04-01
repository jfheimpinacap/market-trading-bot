from __future__ import annotations

from decimal import Decimal

from apps.risk_agent.models import RiskApprovalDecision, RiskRuntimeApprovalStatus, RiskRuntimeCandidate


def build_approval_decision(*, candidate: RiskRuntimeCandidate) -> RiskApprovalDecision:
    reason_codes: list[str] = []
    blockers: list[str] = []

    confidence = Decimal(str(candidate.confidence_score or '0'))
    uncertainty = Decimal(str(candidate.uncertainty_score or '0'))
    adjusted_edge = Decimal(str(candidate.adjusted_edge or '0'))
    evidence_quality = Decimal(str(candidate.evidence_quality_score or '0'))
    caution = Decimal(str(candidate.precedent_caution_score or '0'))
    liquidity_bucket = (candidate.market_liquidity_context or {}).get('bucket', 'unknown')
    ttl_hours = candidate.time_to_resolution

    risk_score = Decimal('0.52')
    risk_score += uncertainty * Decimal('0.30')
    risk_score += caution * Decimal('0.25')
    risk_score += (Decimal('1.00') - confidence) * Decimal('0.30')
    risk_score += (Decimal('1.00') - evidence_quality) * Decimal('0.20')

    if liquidity_bucket == 'thin':
        risk_score += Decimal('0.10')
        reason_codes.append('LIQUIDITY_THIN')
    if liquidity_bucket == 'poor':
        risk_score += Decimal('0.22')
        blockers.append('POOR_LIQUIDITY')
    if ttl_hours is not None and ttl_hours <= 6:
        risk_score += Decimal('0.10')
        reason_codes.append('NEAR_RESOLUTION_WINDOW')

    if candidate.intake_status == 'BLOCKED':
        blockers.append('INTAKE_BLOCKED')
    if candidate.intake_status == 'INSUFFICIENT_CONTEXT':
        blockers.append('INSUFFICIENT_CONTEXT')

    if confidence < Decimal('0.42'):
        blockers.append('LOW_CONFIDENCE')
    if uncertainty > Decimal('0.72'):
        blockers.append('HIGH_UNCERTAINTY')
    if adjusted_edge < Decimal('0.0200'):
        blockers.append('INSUFFICIENT_EDGE')

    if caution >= Decimal('0.75'):
        reason_codes.append('HIGH_PRECEDENT_CAUTION')
    elif caution <= Decimal('0.20'):
        reason_codes.append('LOW_PRECEDENT_CAUTION')

    if 'INSUFFICIENT_CONTEXT' in blockers:
        approval_status = RiskRuntimeApprovalStatus.NEEDS_REVIEW
        watch_required = True
    elif blockers:
        approval_status = RiskRuntimeApprovalStatus.BLOCKED
        watch_required = True
    elif confidence < Decimal('0.58') or uncertainty > Decimal('0.55') or caution > Decimal('0.60'):
        approval_status = RiskRuntimeApprovalStatus.APPROVED_REDUCED
        watch_required = True
    elif evidence_quality < Decimal('0.45'):
        approval_status = RiskRuntimeApprovalStatus.NEEDS_REVIEW
        watch_required = True
        reason_codes.append('EVIDENCE_NEEDS_REVIEW')
    else:
        approval_status = RiskRuntimeApprovalStatus.APPROVED
        watch_required = True

    max_allowed_exposure = Decimal('350.00')
    if approval_status == RiskRuntimeApprovalStatus.APPROVED_REDUCED:
        max_allowed_exposure = Decimal('180.00')
    if approval_status in {RiskRuntimeApprovalStatus.BLOCKED, RiskRuntimeApprovalStatus.NEEDS_REVIEW}:
        max_allowed_exposure = Decimal('0.00')

    rationale = (
        f'confidence={confidence}, uncertainty={uncertainty}, edge={adjusted_edge}, '
        f'liquidity={liquidity_bucket}, evidence_quality={evidence_quality}, precedent_caution={caution}, '
        f'intake_status={candidate.intake_status}, portfolio_pressure={candidate.portfolio_pressure_state}.'
    )
    approval_confidence = max(Decimal('0.0000'), min(Decimal('1.0000'), confidence - (uncertainty * Decimal('0.35'))))

    return RiskApprovalDecision.objects.create(
        linked_candidate=candidate,
        approval_status=approval_status,
        approval_confidence=approval_confidence,
        approval_summary=f'Risk approval review {approval_status} for market {candidate.linked_market_id}.',
        approval_rationale=rationale,
        reason_codes=reason_codes,
        blockers=blockers,
        risk_score=min(max(risk_score, Decimal('0.0000')), Decimal('1.0000')),
        max_allowed_exposure=max_allowed_exposure,
        watch_required=watch_required,
        metadata={
            'paper_demo_only': True,
            'manual_first': True,
            'no_live_execution': True,
        },
    )
