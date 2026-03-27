from __future__ import annotations

from decimal import Decimal

from apps.champion_challenger.models import ChampionChallengerRun, ChampionChallengerRunStatus, StackProfileBinding
from apps.champion_challenger.services.bindings import get_or_create_champion_binding
from apps.memory_retrieval.models import RetrievedPrecedent
from apps.portfolio_governor.models import PortfolioGovernanceRun
from apps.prediction_training.models import PredictionModelArtifact
from apps.profile_manager.models import ProfileGovernanceRun
from apps.readiness_lab.models import ReadinessAssessmentRun

from apps.promotion_committee.models import StackEvidenceSnapshot


def _to_float(value: Decimal | str | int | float | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def build_stack_evidence_snapshot(*, challenger_binding_id: int | None = None, metadata: dict | None = None) -> StackEvidenceSnapshot:
    champion_binding = get_or_create_champion_binding()
    challenger_binding = StackProfileBinding.objects.filter(id=challenger_binding_id).first() if challenger_binding_id else None

    latest_cc = ChampionChallengerRun.objects.select_related('champion_binding', 'challenger_binding').prefetch_related('comparison_result').filter(status=ChampionChallengerRunStatus.COMPLETED).order_by('-created_at', '-id').first()
    latest_readiness = ReadinessAssessmentRun.objects.select_related('readiness_profile').order_by('-created_at', '-id').first()
    latest_profile = ProfileGovernanceRun.objects.order_by('-created_at', '-id').first()
    latest_portfolio = PortfolioGovernanceRun.objects.select_related('throttle_decision').order_by('-created_at', '-id').first()
    active_model = PredictionModelArtifact.objects.filter(is_active=True).order_by('-updated_at', '-id').first()

    precedent_rows = RetrievedPrecedent.objects.select_related('memory_document').order_by('-created_at', '-id')[:5]
    precedent_warnings = [
        {
            'document_type': row.memory_document.document_type,
            'title': row.memory_document.title,
            'short_reason': row.short_reason,
            'similarity_score': row.similarity_score,
        }
        for row in precedent_rows
        if 'risk' in row.short_reason.lower() or 'caution' in row.short_reason.lower() or row.similarity_score >= 0.85
    ]

    comparison_deltas = (latest_cc.comparison_result.deltas if latest_cc and hasattr(latest_cc, 'comparison_result') else {}) or {}
    execution_aware_metrics = {
        'pnl_delta_execution_adjusted': _to_float(comparison_deltas.get('execution_adjusted_pnl_delta')),
        'fill_rate_delta': _to_float(comparison_deltas.get('fill_rate_delta')),
        'no_fill_rate_delta': _to_float(comparison_deltas.get('no_fill_rate_delta')),
        'execution_drag_delta': _to_float(comparison_deltas.get('execution_drag_delta')),
        'drawdown_proxy_delta': _to_float(comparison_deltas.get('drawdown_proxy_delta')),
        'divergence_rate': _to_float(getattr(getattr(latest_cc, 'comparison_result', None), 'decision_divergence_rate', 0)),
        'queue_pressure_delta': _to_float(comparison_deltas.get('risk_review_pressure_delta')),
    }

    return StackEvidenceSnapshot.objects.create(
        champion_binding=champion_binding,
        challenger_binding=challenger_binding or (latest_cc.challenger_binding if latest_cc else None),
        champion_challenger_summary={
            'run_id': latest_cc.id if latest_cc else None,
            'recommendation_code': latest_cc.recommendation_code if latest_cc else None,
            'summary': latest_cc.summary if latest_cc else 'No champion-challenger run available.',
            'reason_codes': latest_cc.recommendation_reasons if latest_cc else [],
            'sample_size': {
                'markets_evaluated': latest_cc.markets_evaluated if latest_cc else 0,
                'opportunities_compared': latest_cc.opportunities_compared if latest_cc else 0,
                'proposals_compared': latest_cc.proposals_compared if latest_cc else 0,
                'fills_compared': latest_cc.fills_compared if latest_cc else 0,
            },
        },
        execution_aware_metrics=execution_aware_metrics,
        readiness_summary={
            'run_id': latest_readiness.id if latest_readiness else None,
            'status': latest_readiness.status if latest_readiness else 'UNKNOWN',
            'score': float(latest_readiness.overall_score or 0) if latest_readiness else None,
            'summary': latest_readiness.summary if latest_readiness else 'No readiness run available.',
        },
        profile_governance_context={
            'run_id': latest_profile.id if latest_profile else None,
            'regime': latest_profile.regime if latest_profile else 'UNKNOWN',
            'runtime_mode': latest_profile.runtime_mode if latest_profile else '',
            'readiness_status': latest_profile.readiness_status if latest_profile else '',
            'summary': latest_profile.summary if latest_profile else 'No profile governance run available.',
        },
        portfolio_governor_context={
            'run_id': latest_portfolio.id if latest_portfolio else None,
            'throttle_state': latest_portfolio.throttle_decision.state if latest_portfolio and latest_portfolio.throttle_decision else 'UNKNOWN',
            'reason_codes': latest_portfolio.throttle_decision.reason_codes if latest_portfolio and latest_portfolio.throttle_decision else [],
            'summary': latest_portfolio.summary if latest_portfolio else 'No portfolio governor run available.',
        },
        model_governance_summary={
            'active_model_artifact_id': active_model.id if active_model else None,
            'active_model_name': active_model.name if active_model else None,
            'active_model_version': active_model.version if active_model else None,
        },
        precedent_warnings=precedent_warnings,
        metadata=metadata or {},
    )
