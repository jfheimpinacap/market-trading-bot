from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.learning_memory.models import LearningAdjustment, LearningAdjustmentType, LearningScopeType
from apps.markets.models import MarketSourceType
from apps.policy_engine.models import ApprovalDecisionType
from apps.proposal_engine.models import TradeProposal
from apps.real_data_sync.services import build_sync_status
from apps.risk_demo.models import TradeRiskDecision


@dataclass
class RankedProposal:
    proposal: TradeProposal
    rank_score: Decimal
    penalties: list[str]



def _decimal(value: Decimal | int | float | None, fallback: str = '0') -> Decimal:
    if value is None:
        return Decimal(fallback)
    return Decimal(str(value))


def rank_proposals(*, proposals: list[TradeProposal], prefer_real_markets: bool, penalize_existing_exposure: bool, exposure_by_market: dict[int, Decimal], penalize_degraded_provider: bool, penalize_unfavorable_learning: bool) -> list[RankedProposal]:
    status_snapshot = build_sync_status()['providers']

    learning_penalties: dict[str, Decimal] = {}
    if penalize_unfavorable_learning:
        for adj in LearningAdjustment.objects.filter(is_active=True):
            learning_penalties[f'{adj.adjustment_type}:{adj.scope_type}:{adj.scope_key}'] = adj.magnitude

    ranked: list[RankedProposal] = []
    for proposal in proposals:
        score = _decimal(proposal.proposal_score) * Decimal('0.60') + _decimal(proposal.confidence) * Decimal('25.00')
        penalties: list[str] = []

        if proposal.policy_decision == ApprovalDecisionType.HARD_BLOCK:
            score -= Decimal('1000.00')
            penalties.append('policy_hard_block')
        elif proposal.policy_decision == ApprovalDecisionType.APPROVAL_REQUIRED:
            score -= Decimal('12.00')
            penalties.append('policy_approval_required')
        else:
            score += Decimal('8.00')

        if proposal.risk_decision == TradeRiskDecision.BLOCK:
            score -= Decimal('200.00')
            penalties.append('risk_block')
        elif proposal.risk_decision == TradeRiskDecision.CAUTION:
            score -= Decimal('6.00')
            penalties.append('risk_caution')
        else:
            score += Decimal('5.00')

        if prefer_real_markets:
            if proposal.market.source_type == MarketSourceType.REAL_READ_ONLY:
                score += Decimal('3.00')
            else:
                score -= Decimal('1.00')

        if penalize_existing_exposure:
            exposure = exposure_by_market.get(proposal.market_id, Decimal('0.00'))
            if exposure > Decimal('0.00'):
                score -= Decimal('8.00')
                penalties.append('existing_market_exposure')

        if penalize_degraded_provider and proposal.market.source_type == MarketSourceType.REAL_READ_ONLY:
            provider_status = status_snapshot.get(proposal.market.provider.slug, {})
            if provider_status.get('stale'):
                score -= Decimal('16.00')
                penalties.append('provider_stale')
            if provider_status.get('availability') == 'degraded':
                score -= Decimal('12.00')
                penalties.append('provider_degraded')

        liquidity = proposal.market.liquidity or Decimal('0')
        if liquidity < Decimal('100'):
            score -= Decimal('4.00')
            penalties.append('low_liquidity')

        volume_24h = proposal.market.volume_24h or Decimal('0')
        if volume_24h < Decimal('100'):
            score -= Decimal('3.00')
            penalties.append('low_volume_24h')

        if penalize_unfavorable_learning:
            source_key = f"{LearningAdjustmentType.QUANTITY_BIAS}:{LearningScopeType.SOURCE_TYPE}:{proposal.market.source_type}"
            provider_key = f"{LearningAdjustmentType.RISK_CAUTION_BIAS}:{LearningScopeType.PROVIDER}:{proposal.market.provider.slug}"
            global_key = f"{LearningAdjustmentType.CONFIDENCE_BIAS}:{LearningScopeType.GLOBAL}:global"
            for key in (source_key, provider_key, global_key):
                magnitude = learning_penalties.get(key, Decimal('0.0000'))
                if magnitude < Decimal('0.0000'):
                    score += magnitude * Decimal('20.00')
                    penalties.append(f'learning_penalty:{key}')

        ranked.append(RankedProposal(proposal=proposal, rank_score=score.quantize(Decimal('0.01')), penalties=penalties))

    return sorted(ranked, key=lambda item: (item.rank_score, item.proposal.created_at), reverse=True)
