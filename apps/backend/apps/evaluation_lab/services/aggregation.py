from decimal import Decimal

from django.db.models import Avg, Max, Min, Sum

from apps.continuous_demo.models import ContinuousDemoCycleRun, ContinuousDemoSession
from apps.evaluation_lab.models import EvaluationMarketScope, EvaluationMetricSet, EvaluationRun, EvaluationRunStatus, EvaluationScope
from apps.markets.models import MarketSourceType
from apps.paper_trading.models import PaperPortfolioSnapshot, PaperTrade
from apps.postmortem_demo.models import TradeReview, TradeReviewOutcome
from apps.proposal_engine.models import TradeProposal
from apps.safety_guard.models import SafetyEvent, SafetyEventType
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus, SemiAutoRun

from .execution_metrics import build_execution_metrics, merge_execution_pnl
from .metrics import build_guidance, safe_rate


def _to_decimal(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal('0')


def _resolve_market_scope(run: EvaluationRun) -> str:
    if run.related_continuous_session and run.related_continuous_session.settings_snapshot.get('market_scope') in {'demo_only', 'real_only', 'mixed'}:
        return run.related_continuous_session.settings_snapshot.get('market_scope')
    if run.related_semi_auto_run:
        return EvaluationMarketScope.MIXED
    return run.market_scope


def build_metrics_for_run(run: EvaluationRun) -> EvaluationMetricSet:
    started_at = run.started_at
    finished_at = run.finished_at or run.started_at

    cycle_qs = ContinuousDemoCycleRun.objects.filter(started_at__gte=started_at, started_at__lte=finished_at)
    if run.related_continuous_session_id:
        cycle_qs = cycle_qs.filter(session_id=run.related_continuous_session_id)

    proposals_qs = TradeProposal.objects.filter(created_at__gte=started_at, created_at__lte=finished_at)
    trades_qs = PaperTrade.objects.select_related('market').filter(executed_at__gte=started_at, executed_at__lte=finished_at)
    reviews_qs = TradeReview.objects.filter(reviewed_at__gte=started_at, reviewed_at__lte=finished_at)
    safety_qs = SafetyEvent.objects.filter(created_at__gte=started_at, created_at__lte=finished_at)
    pending_qs = PendingApproval.objects.filter(created_at__gte=started_at, created_at__lte=finished_at)

    proposals_generated = proposals_qs.count()
    auto_executed_count = cycle_qs.aggregate(total=Sum('auto_executed_count')).get('total') or 0
    approval_required_count = cycle_qs.aggregate(total=Sum('approval_required_count')).get('total') or 0
    blocked_count = cycle_qs.aggregate(total=Sum('blocked_count')).get('total') or 0

    pending_approvals_count = pending_qs.filter(status=PendingApprovalStatus.PENDING).count()
    executed_pending_count = pending_qs.filter(status=PendingApprovalStatus.EXECUTED).count()
    manual_approved_count = pending_qs.filter(status=PendingApprovalStatus.APPROVED).count() + executed_pending_count

    trades_executed_count = trades_qs.count()
    reviews_generated_count = reviews_qs.count()
    favorable_reviews_count = reviews_qs.filter(outcome=TradeReviewOutcome.FAVORABLE).count()
    neutral_reviews_count = reviews_qs.filter(outcome=TradeReviewOutcome.NEUTRAL).count()
    unfavorable_reviews_count = reviews_qs.filter(outcome=TradeReviewOutcome.UNFAVORABLE).count()

    account_snapshot = (
        PaperPortfolioSnapshot.objects.filter(captured_at__lte=finished_at)
        .order_by('-captured_at', '-id')
        .first()
    )
    account_snapshot_start = (
        PaperPortfolioSnapshot.objects.filter(captured_at__gte=started_at)
        .order_by('captured_at', 'id')
        .first()
    )

    ending_equity = _to_decimal(account_snapshot.equity) if account_snapshot else Decimal('0')
    starting_equity = _to_decimal(account_snapshot_start.equity) if account_snapshot_start else ending_equity

    proposal_scores = proposals_qs.aggregate(avg_score=Avg('proposal_score'), avg_confidence=Avg('confidence'))

    real_trades = trades_qs.filter(market__source_type=MarketSourceType.REAL_READ_ONLY).count()
    demo_trades = trades_qs.filter(market__source_type=MarketSourceType.DEMO).count()

    unfavorable_streak = 0
    for outcome in reviews_qs.order_by('-reviewed_at').values_list('outcome', flat=True):
        if outcome == TradeReviewOutcome.UNFAVORABLE:
            unfavorable_streak += 1
            continue
        break

    metrics = {
        'cycles_count': cycle_qs.count(),
        'proposals_generated': proposals_generated,
        'auto_executed_count': auto_executed_count,
        'approval_required_count': approval_required_count,
        'blocked_count': blocked_count,
        'pending_approvals_count': pending_approvals_count,
        'trades_executed_count': trades_executed_count,
        'reviews_generated_count': reviews_generated_count,
        'favorable_reviews_count': favorable_reviews_count,
        'neutral_reviews_count': neutral_reviews_count,
        'unfavorable_reviews_count': unfavorable_reviews_count,
        'approval_rate': safe_rate(approval_required_count, proposals_generated),
        'block_rate': safe_rate(blocked_count, proposals_generated),
        'auto_execution_rate': safe_rate(auto_executed_count, proposals_generated),
        'favorable_review_rate': safe_rate(favorable_reviews_count, reviews_generated_count),
        'total_realized_pnl': _to_decimal(account_snapshot.realized_pnl) if account_snapshot else Decimal('0'),
        'total_unrealized_pnl': _to_decimal(account_snapshot.unrealized_pnl) if account_snapshot else Decimal('0'),
        'total_pnl': _to_decimal(account_snapshot.total_pnl) if account_snapshot else Decimal('0'),
        'ending_equity': ending_equity,
        'equity_delta': ending_equity - starting_equity,
        'safety_events_count': safety_qs.count(),
        'cooldown_count': safety_qs.filter(event_type=SafetyEventType.COOLDOWN_TRIGGERED).count(),
        'hard_stop_count': safety_qs.filter(event_type=SafetyEventType.HARD_STOP_TRIGGERED).count(),
        'kill_switch_count': safety_qs.filter(event_type=SafetyEventType.KILL_SWITCH_TRIGGERED).count(),
        'error_count': safety_qs.filter(event_type=SafetyEventType.ERROR_LIMIT_HIT).count(),
        'proposal_to_execution_ratio': safe_rate(trades_executed_count, proposals_generated),
        'execution_to_review_ratio': safe_rate(reviews_generated_count, trades_executed_count),
        'unfavorable_review_streak': unfavorable_streak,
        'average_pnl_per_trade': (ending_equity - starting_equity) / Decimal(trades_executed_count) if trades_executed_count else Decimal('0'),
        'average_proposal_score': _to_decimal(proposal_scores.get('avg_score')),
        'average_confidence': _to_decimal(proposal_scores.get('avg_confidence')),
        'percent_real_market_trades': safe_rate(real_trades, trades_executed_count),
        'percent_demo_market_trades': safe_rate(demo_trades, trades_executed_count),
        'percent_auto_approved': safe_rate(auto_executed_count, auto_executed_count + manual_approved_count),
        'percent_manual_approved': safe_rate(manual_approved_count, auto_executed_count + manual_approved_count),
    }
    execution_metrics = merge_execution_pnl(
        total_pnl=metrics['total_pnl'],
        execution_metrics=build_execution_metrics(started_at=started_at, finished_at=finished_at),
    )

    guidance = build_guidance(metrics)
    run.market_scope = _resolve_market_scope(run)
    run.status = EvaluationRunStatus.READY
    run.summary = (
        f"{metrics['proposals_generated']} proposals, {metrics['trades_executed_count']} executed trades, "
        f"block rate {metrics['block_rate']}, favorable reviews {metrics['favorable_review_rate']}."
    )
    run.guidance = guidance
    run.metadata = {
        **(run.metadata or {}),
        'execution_adjusted_snapshot': execution_metrics,
    }
    run.save(update_fields=['market_scope', 'status', 'summary', 'guidance', 'metadata', 'updated_at'])

    metric_set, _ = EvaluationMetricSet.objects.update_or_create(run=run, defaults=metrics)
    return metric_set


def build_run_for_continuous_session(session: ContinuousDemoSession) -> EvaluationRun:
    run = EvaluationRun.objects.create(
        related_continuous_session=session,
        evaluation_scope=EvaluationScope.SESSION,
        market_scope=session.settings_snapshot.get('market_scope', EvaluationMarketScope.MIXED),
        started_at=session.started_at,
        finished_at=session.finished_at or session.last_cycle_at or session.started_at,
        status=EvaluationRunStatus.IN_PROGRESS,
        summary='Building metrics.',
    )
    build_metrics_for_run(run)
    return run


def build_run_for_semi_auto(run_obj: SemiAutoRun) -> EvaluationRun:
    run = EvaluationRun.objects.create(
        related_semi_auto_run=run_obj,
        evaluation_scope=EvaluationScope.SESSION,
        market_scope=EvaluationMarketScope.MIXED,
        started_at=run_obj.started_at,
        finished_at=run_obj.finished_at or run_obj.started_at,
        status=EvaluationRunStatus.IN_PROGRESS,
        summary='Building metrics.',
    )
    build_metrics_for_run(run)
    return run
