from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.markets.models import Market
from apps.prediction_agent.models import PredictionScore
from apps.proposal_engine.models import TradeProposal
from apps.research_agent.models import MarketUniverseScanRun, PursuitCandidate, TriageStatus
from apps.risk_agent.models import RiskAssessment, RiskLevel, RiskSizingDecision
from apps.runtime_governor.models import RuntimeModeState
from apps.safety_guard.models import SafetyPolicyConfig
from apps.signals.models import OpportunitySignal, OpportunityStatus, ProposalGateDecision, SignalFusionRun, SignalRunStatus
from apps.signals.services.gating import build_proposal_gate_decision
from apps.signals.services.profiles import get_profile
from apps.signals.services.ranking import rank_opportunities


RISK_SCORES = {
    RiskLevel.LOW: Decimal('1.00'),
    RiskLevel.MEDIUM: Decimal('0.62'),
    RiskLevel.HIGH: Decimal('0.30'),
    RiskLevel.BLOCKED: Decimal('0.00'),
}


def _normalize_score_0_100(value: Decimal | None, default: Decimal = Decimal('0.00')) -> Decimal:
    if value is None:
        return default
    return max(Decimal('0.00'), min(Decimal('100.00'), value))


def _to_score_from_probability(value: Decimal | None, default: Decimal = Decimal('0.00')) -> Decimal:
    if value is None:
        return default
    return _normalize_score_0_100(value * Decimal('100'))


def _safe_decimal(value, default: Decimal = Decimal('0.00')) -> Decimal:
    if value is None:
        return default
    return Decimal(str(value))


def _latest_by_market(queryset, market_field: str = 'market_id'):
    latest = {}
    for item in queryset.order_by('-created_at', '-id'):
        market_id = getattr(item, market_field)
        if market_id not in latest:
            latest[market_id] = item
    return latest


def _compute_status(*, risk_level: str, runtime_status: str, safety_status: str, runtime_allows_proposals: bool, score: Decimal, edge: Decimal, prediction_confidence: Decimal, profile):
    if risk_level == RiskLevel.BLOCKED or runtime_status in {'PAUSED', 'STOPPED'} or safety_status in {'KILL_SWITCH', 'HARD_STOP', 'PAUSED'}:
        return OpportunityStatus.BLOCKED
    if not runtime_allows_proposals:
        return OpportunityStatus.WATCH
    if risk_level == RiskLevel.HIGH:
        return OpportunityStatus.WATCH
    if score >= profile.proposal_ready_score and edge >= profile.min_edge_for_proposal and prediction_confidence >= profile.min_confidence_for_proposal:
        return OpportunityStatus.PROPOSAL_READY
    if score >= profile.candidate_score:
        return OpportunityStatus.CANDIDATE
    return OpportunityStatus.WATCH


@transaction.atomic
def run_signal_fusion(*, profile_slug: str | None = None, market_ids: list[int] | None = None, triggered_by: str = 'manual_api') -> SignalFusionRun:
    profile = get_profile(profile_slug)
    run = SignalFusionRun.objects.create(
        status=SignalRunStatus.RUNNING,
        profile_slug=profile.slug,
        triggered_by=triggered_by,
        metadata={
            'weights': {
                'research': str(profile.research_weight),
                'prediction': str(profile.prediction_weight),
                'risk': str(profile.risk_weight),
            }
        },
    )

    runtime_state = RuntimeModeState.objects.order_by('-effective_at', '-id').first()
    safety_config = SafetyPolicyConfig.objects.order_by('-updated_at', '-id').first()

    latest_universe_run = MarketUniverseScanRun.objects.order_by('-started_at', '-id').first()
    candidates_qs = PursuitCandidate.objects.select_related('market', 'market__provider').order_by('-created_at', '-id')
    if latest_universe_run:
        candidates_qs = candidates_qs.filter(run_id=latest_universe_run.id)
    pursuit_by_market = _latest_by_market(candidates_qs, 'market_id')

    prediction_by_market = _latest_by_market(PredictionScore.objects.select_related('market', 'market__provider').all(), 'market_id')
    assessments_by_market = _latest_by_market(RiskAssessment.objects.select_related('market', 'prediction_score').all(), 'market_id')
    sizings_by_assessment = {}
    for sizing in RiskSizingDecision.objects.select_related('risk_assessment').order_by('-created_at', '-id'):
        if sizing.risk_assessment_id not in sizings_by_assessment:
            sizings_by_assessment[sizing.risk_assessment_id] = sizing

    market_ids_set = set(pursuit_by_market.keys()) | set(prediction_by_market.keys()) | set(assessments_by_market.keys())
    if market_ids:
        market_ids_set = market_ids_set & set(market_ids)

    markets = Market.objects.select_related('provider').filter(id__in=market_ids_set).order_by('id')

    created = []
    for market in markets:
        pursuit = pursuit_by_market.get(market.id)
        prediction = prediction_by_market.get(market.id)
        assessment = assessments_by_market.get(market.id)
        sizing = sizings_by_assessment.get(assessment.id) if assessment else None

        triage_score = _safe_decimal(pursuit.triage_score if pursuit else Decimal('0.00'))
        research_score = _normalize_score_0_100(triage_score)
        edge = _safe_decimal(prediction.edge if prediction else Decimal('0.0000'))
        prediction_confidence = _safe_decimal(prediction.confidence if prediction else Decimal('0.0000'))
        prediction_score = _normalize_score_0_100(abs(edge) * Decimal('1000') + _to_score_from_probability(prediction_confidence) * Decimal('0.35'))

        risk_level = assessment.risk_level if assessment else RiskLevel.MEDIUM
        risk_score = _normalize_score_0_100(RISK_SCORES.get(risk_level, Decimal('0.50')) * Decimal('100'))

        runtime_status = runtime_state.status if runtime_state else 'ACTIVE'
        runtime_mode = runtime_state.current_mode if runtime_state else 'OBSERVE_ONLY'
        runtime_allows_proposals = runtime_mode in {'PAPER_ASSIST', 'PAPER_SEMI_AUTO', 'PAPER_AUTO'} and runtime_status == 'ACTIVE'
        safety_status = safety_config.status if safety_config else 'HEALTHY'

        opportunity_score = (
            research_score * profile.research_weight
            + prediction_score * profile.prediction_weight
            + risk_score * profile.risk_weight
        ).quantize(Decimal('0.01'))

        narrative_direction = pursuit.narrative_direction if pursuit else 'uncertain'
        source_mix = pursuit.source_mix if pursuit else 'none'

        status = _compute_status(
            risk_level=risk_level,
            runtime_status=runtime_status,
            safety_status=safety_status,
            runtime_allows_proposals=runtime_allows_proposals,
            score=opportunity_score,
            edge=edge,
            prediction_confidence=prediction_confidence,
            profile=profile,
        )

        rationale = (
            f'Research={research_score:.2f}, Prediction={prediction_score:.2f}, Risk={risk_score:.2f}. '
            f'Edge={edge:+.2%}, confidence={prediction_confidence:.2%}, risk={risk_level}. '
            f'Runtime={runtime_mode}/{runtime_status}, safety={safety_status}.'
        )
        if pursuit and pursuit.triage_status == TriageStatus.FILTERED_OUT:
            status = OpportunityStatus.BLOCKED
            rationale = f'Research triage filtered this market out. {rationale}'

        opportunity = OpportunitySignal.objects.create(
            run=run,
            market=market,
            provider_slug=market.provider.slug if market.provider_id else '',
            research_score=research_score,
            triage_score=triage_score,
            narrative_direction=narrative_direction,
            narrative_confidence=Decimal(str(pursuit.details.get('narrative_confidence', '0.0000'))) if pursuit else Decimal('0.0000'),
            source_mix=source_mix,
            prediction_system_probability=prediction.system_probability if prediction else None,
            prediction_market_probability=prediction.market_probability if prediction else None,
            edge=edge,
            prediction_confidence=prediction_confidence,
            risk_level=risk_level,
            adjusted_quantity=sizing.adjusted_quantity if sizing else None,
            runtime_constraints={
                'runtime_mode': runtime_mode,
                'runtime_status': runtime_status,
                'runtime_allow_proposals': runtime_allows_proposals,
                'safety_status': safety_status,
                'paper_demo_only': True,
                'real_execution_enabled': False,
            },
            opportunity_score=opportunity_score,
            opportunity_status=status,
            rationale=rationale,
            metadata={
                'research': {'pursuit_candidate_id': pursuit.id if pursuit else None},
                'prediction': {'prediction_score_id': prediction.id if prediction else None},
                'risk': {'risk_assessment_id': assessment.id if assessment else None, 'risk_sizing_id': sizing.id if sizing else None},
            },
        )

        gate_payload = build_proposal_gate_decision(opportunity=opportunity, profile=profile)
        ProposalGateDecision.objects.create(opportunity=opportunity, **gate_payload)
        created.append(opportunity)

    ordered = rank_opportunities(created)
    for index, opportunity in enumerate(ordered, start=1):
        opportunity.rank = index
        opportunity.save(update_fields=['rank', 'updated_at'])

    run.status = SignalRunStatus.COMPLETED
    run.finished_at = timezone.now()
    run.markets_evaluated = len(created)
    run.signals_created = len(created)
    run.proposal_ready_count = len([item for item in created if item.opportunity_status == OpportunityStatus.PROPOSAL_READY])
    run.blocked_count = len([item for item in created if item.opportunity_status == OpportunityStatus.BLOCKED])
    run.metadata = {
        **run.metadata,
        'runtime_mode': runtime_mode if runtime_state else None,
        'runtime_status': runtime_status if runtime_state else None,
        'safety_status': safety_status if safety_config else None,
        'profile': profile.slug,
    }
    run.save()
    return run


def run_fusion_to_proposal(*, run: SignalFusionRun, min_priority: int = 70):
    created = []
    opportunities = run.opportunities.select_related('market', 'proposal_gate').filter(opportunity_status=OpportunityStatus.PROPOSAL_READY)
    for opportunity in opportunities:
        gate = getattr(opportunity, 'proposal_gate', None)
        if not gate or not gate.should_generate_proposal or gate.proposal_priority < min_priority:
            continue
        proposal = TradeProposal.objects.create(
            market=opportunity.market,
            proposal_status='ACTIVE',
            direction='BUY_YES' if (opportunity.prediction_system_probability or Decimal('0.5')) >= Decimal('0.5') else 'BUY_NO',
            proposal_score=opportunity.opportunity_score,
            confidence=opportunity.prediction_confidence,
            headline=f'Fusion proposal candidate for {opportunity.market.title}',
            thesis=opportunity.rationale,
            rationale=f'Generated from signal fusion run #{run.id}.',
            suggested_trade_type='BUY',
            suggested_side='YES' if (opportunity.prediction_system_probability or Decimal('0.5')) >= Decimal('0.5') else 'NO',
            suggested_quantity=opportunity.adjusted_quantity,
            suggested_price_reference=opportunity.prediction_market_probability,
            risk_decision='CAUTION',
            policy_decision='APPROVAL_REQUIRED',
            approval_required=True,
            is_actionable=False,
            recommendation='Review manually before any paper trade action.',
            metadata={'source': 'signal_fusion', 'signal_fusion_run_id': run.id, 'opportunity_signal_id': opportunity.id},
        )
        created.append(proposal)
    return created
