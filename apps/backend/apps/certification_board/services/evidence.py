from __future__ import annotations

from django.db.models import Avg, Count

from apps.chaos_lab.models import ResilienceBenchmark
from apps.champion_challenger.models import ChampionChallengerRun
from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.incident_commander.models import DegradedModeState, IncidentRecord
from apps.portfolio_governor.models import PortfolioGovernanceRun
from apps.profile_manager.models import ProfileDecision, ProfileGovernanceRun
from apps.promotion_committee.models import PromotionReviewRun
from apps.readiness_lab.models import ReadinessAssessmentRun
from apps.rollout_manager.models import RolloutGuardrailEvent, StackRolloutRun
from apps.runtime_governor.models import RuntimeModeState
from apps.safety_guard.models import SafetyPolicyConfig
from apps.certification_board.models import CertificationEvidenceSnapshot


def _as_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def build_evidence_snapshot(*, metadata: dict | None = None) -> CertificationEvidenceSnapshot:
    readiness = ReadinessAssessmentRun.objects.order_by('-created_at', '-id').first()
    evaluation = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id').first()
    champion = ChampionChallengerRun.objects.order_by('-created_at', '-id').first()
    promotion = PromotionReviewRun.objects.order_by('-created_at', '-id').first()
    rollout = StackRolloutRun.objects.select_related('plan').order_by('-created_at', '-id').first()
    degraded_state = DegradedModeState.objects.order_by('-updated_at', '-id').first()
    portfolio = PortfolioGovernanceRun.objects.select_related('throttle_decision').order_by('-started_at', '-id').first()
    profile_run = ProfileGovernanceRun.objects.order_by('-started_at', '-id').first()
    profile_decision = ProfileDecision.objects.select_related('run').order_by('-created_at', '-id').first()
    runtime = RuntimeModeState.objects.order_by('-updated_at', '-id').first()
    safety = SafetyPolicyConfig.objects.order_by('id').first()

    incident_base = IncidentRecord.objects.order_by('-last_seen_at', '-id')
    recent_incidents = incident_base[:30]
    open_critical = incident_base.filter(severity='critical', status__in=['OPEN', 'MITIGATING', 'ESCALATED']).count()
    open_high = incident_base.filter(severity='high', status__in=['OPEN', 'MITIGATING', 'ESCALATED']).count()

    latest_chaos = ResilienceBenchmark.objects.select_related('run', 'experiment').order_by('-created_at', '-id').first()
    chaos_agg = ResilienceBenchmark.objects.aggregate(
        avg_score=Avg('resilience_score'),
        avg_recovery=Avg('recovery_success_rate'),
        rollback_count=Count('id', filter=None),
    )
    guardrail_base = RolloutGuardrailEvent.objects.order_by('-created_at', '-id')

    evaluation_metrics = evaluation.metric_set if evaluation and hasattr(evaluation, 'metric_set') else None

    snapshot = CertificationEvidenceSnapshot.objects.create(
        readiness_summary={
            'status': readiness.status if readiness else 'UNKNOWN',
            'score': _as_float(readiness.overall_score) if readiness else None,
            'summary': readiness.summary if readiness else 'No readiness run found.',
            'warnings_count': readiness.warnings_count if readiness else 0,
            'critical_blockers': len((readiness.details or {}).get('critical_blockers', [])) if readiness else 0,
        },
        execution_evaluation_summary={
            'status': evaluation.status if evaluation else 'UNKNOWN',
            'market_scope': evaluation.market_scope if evaluation else 'unknown',
            'favorable_review_rate': _as_float(getattr(evaluation_metrics, 'favorable_review_rate', 0)),
            'block_rate': _as_float(getattr(evaluation_metrics, 'block_rate', 0)),
            'hard_stop_count': int(getattr(evaluation_metrics, 'hard_stop_count', 0) or 0),
            'safety_events_count': int(getattr(evaluation_metrics, 'safety_events_count', 0) or 0),
            'execution_realism_score': _as_float((evaluation.metadata or {}).get('execution_realism_score', 0)) if evaluation else 0,
        },
        champion_challenger_summary={
            'status': champion.status if champion else 'UNKNOWN',
            'recommendation_code': champion.recommendation_code if champion else 'UNKNOWN',
            'markets_evaluated': champion.markets_evaluated if champion else 0,
            'pnl_delta_execution_adjusted': _as_float(champion.pnl_delta_execution_adjusted) if champion else 0,
        },
        promotion_summary={
            'recommendation_code': promotion.recommendation_code if promotion else 'UNKNOWN',
            'confidence': _as_float(promotion.confidence) if promotion else 0,
            'blocking_constraints': promotion.blocking_constraints if promotion else [],
        },
        rollout_summary={
            'status': rollout.status if rollout else 'UNKNOWN',
            'mode': rollout.plan.mode if rollout and rollout.plan else 'UNKNOWN',
            'guardrail_warning_count': guardrail_base.filter(severity='WARNING').count(),
            'guardrail_critical_count': guardrail_base.filter(severity='CRITICAL').count(),
        },
        incident_summary={
            'open_critical': open_critical,
            'open_high': open_high,
            'open_total': incident_base.filter(status__in=['OPEN', 'MITIGATING', 'ESCALATED', 'DEGRADED']).count(),
            'recent_total': len(recent_incidents),
        },
        chaos_benchmark_summary={
            'latest_resilience_score': _as_float(latest_chaos.resilience_score) if latest_chaos else 0,
            'latest_recovery_success_rate': _as_float(latest_chaos.recovery_success_rate) if latest_chaos else 0,
            'latest_degraded_mode_triggered': bool(latest_chaos.degraded_mode_triggered) if latest_chaos else False,
            'latest_rollback_triggered': bool(latest_chaos.rollback_triggered) if latest_chaos else False,
            'average_resilience_score': _as_float(chaos_agg['avg_score']),
            'average_recovery_success_rate': _as_float(chaos_agg['avg_recovery']),
        },
        portfolio_governor_summary={
            'run_status': portfolio.status if portfolio else 'UNKNOWN',
            'throttle_state': portfolio.throttle_decision.state if portfolio and portfolio.throttle_decision else 'UNKNOWN',
            'max_new_positions': portfolio.throttle_decision.recommended_max_new_positions if portfolio and portfolio.throttle_decision else 1,
            'max_size_multiplier': _as_float(portfolio.throttle_decision.recommended_max_size_multiplier) if portfolio and portfolio.throttle_decision else 1,
        },
        profile_manager_summary={
            'regime': profile_run.regime if profile_run else 'UNKNOWN',
            'runtime_mode': profile_run.runtime_mode if profile_run else '',
            'target_mission_control_profile': profile_decision.target_mission_control_profile if profile_decision else '',
            'target_portfolio_governor_profile': profile_decision.target_portfolio_governor_profile if profile_decision else '',
        },
        runtime_safety_summary={
            'runtime_mode': runtime.current_mode if runtime else 'UNKNOWN',
            'runtime_status': runtime.status if runtime else 'UNKNOWN',
            'safety_status': safety.status if safety else 'UNKNOWN',
            'kill_switch_enabled': bool(safety.kill_switch_enabled) if safety else False,
            'hard_stop_active': bool(safety.hard_stop_active) if safety else False,
            'paused_by_safety': bool(safety.paused_by_safety) if safety else False,
        },
        degraded_or_rollback_summary={
            'current_state': degraded_state.state if degraded_state else 'normal',
            'mission_control_paused': bool(degraded_state.mission_control_paused) if degraded_state else False,
            'rollout_enabled': bool(degraded_state.rollout_enabled) if degraded_state else True,
            'auto_execution_enabled': bool(degraded_state.auto_execution_enabled) if degraded_state else True,
            'reasons': degraded_state.reasons if degraded_state else [],
        },
        metadata=metadata or {},
    )
    return snapshot
