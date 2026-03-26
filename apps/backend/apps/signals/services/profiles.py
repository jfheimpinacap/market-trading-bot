from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SignalProfileConfig:
    slug: str
    label: str
    description: str
    research_weight: Decimal
    prediction_weight: Decimal
    risk_weight: Decimal
    proposal_ready_score: Decimal
    candidate_score: Decimal
    min_edge_for_proposal: Decimal
    min_confidence_for_proposal: Decimal


DEFAULT_PROFILE = 'balanced_signal'


SIGNAL_PROFILES: dict[str, SignalProfileConfig] = {
    'conservative_signal': SignalProfileConfig(
        slug='conservative_signal',
        label='Conservative signal',
        description='Prioriza control de riesgo y exige mayor calidad antes de abrir propuesta.',
        research_weight=Decimal('0.30'),
        prediction_weight=Decimal('0.35'),
        risk_weight=Decimal('0.35'),
        proposal_ready_score=Decimal('73.00'),
        candidate_score=Decimal('58.00'),
        min_edge_for_proposal=Decimal('0.0350'),
        min_confidence_for_proposal=Decimal('0.6700'),
    ),
    'balanced_signal': SignalProfileConfig(
        slug='balanced_signal',
        label='Balanced signal',
        description='Balancea narrativa, edge y riesgo para un board operativo general.',
        research_weight=Decimal('0.33'),
        prediction_weight=Decimal('0.42'),
        risk_weight=Decimal('0.25'),
        proposal_ready_score=Decimal('68.00'),
        candidate_score=Decimal('52.00'),
        min_edge_for_proposal=Decimal('0.0250'),
        min_confidence_for_proposal=Decimal('0.6000'),
    ),
    'aggressive_light_signal': SignalProfileConfig(
        slug='aggressive_light_signal',
        label='Aggressive light signal',
        description='Más sensible al edge; mantiene bloqueo estricto por seguridad/riesgo.',
        research_weight=Decimal('0.25'),
        prediction_weight=Decimal('0.55'),
        risk_weight=Decimal('0.20'),
        proposal_ready_score=Decimal('64.00'),
        candidate_score=Decimal('48.00'),
        min_edge_for_proposal=Decimal('0.0200'),
        min_confidence_for_proposal=Decimal('0.5400'),
    ),
}


def get_profile(profile_slug: str | None) -> SignalProfileConfig:
    if not profile_slug:
        return SIGNAL_PROFILES[DEFAULT_PROFILE]
    return SIGNAL_PROFILES.get(profile_slug, SIGNAL_PROFILES[DEFAULT_PROFILE])
