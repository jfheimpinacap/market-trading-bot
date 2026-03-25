from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.continuous_demo.models import ContinuousDemoSession
from apps.evaluation_lab.models import EvaluationRun
from apps.evaluation_lab.services import build_run_for_continuous_session
from apps.experiment_lab.models import ExperimentRun, ExperimentRunStatus, ExperimentRunType, StrategyProfile
from apps.replay_lab.models import ReplayRun
from apps.replay_lab.services import run_replay


@dataclass
class ExperimentExecutionResult:
    experiment_run: ExperimentRun


def _as_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal('0')
    return Decimal(str(value))


def _scope_to_replay_source(scope: str) -> str:
    return scope


def _normalize_replay_metrics(run: ReplayRun) -> dict:
    proposals = run.proposals_generated
    trades = run.trades_executed
    approvals_required = run.approvals_required
    blocked = run.blocked_count
    auto_executions = max(trades - approvals_required, 0)

    block_rate = Decimal(blocked) / Decimal(proposals) if proposals else Decimal('0')
    auto_execution_rate = Decimal(auto_executions) / Decimal(trades) if trades else Decimal('0')

    details = run.details or {}

    return {
        'proposals_generated': proposals,
        'trades_executed': trades,
        'approvals_required': approvals_required,
        'blocked_count': blocked,
        'favorable_review_rate': details.get('favorable_review_rate', '0'),
        'total_pnl': str(run.total_pnl),
        'ending_equity': str(run.ending_equity),
        'equity_delta': str(details.get('equity_delta', '0')),
        'safety_events_count': int(details.get('safety_events_count', 0)),
        'cooldown_count': int(details.get('cooldown_count', 0)),
        'hard_stop_count': int(details.get('hard_stop_count', 0)),
        'allocation_efficiency': str(details.get('allocation_efficiency', '0')),
        'block_rate': str(block_rate),
        'auto_execution_rate': str(auto_execution_rate),
    }


def _normalize_evaluation_metrics(run: EvaluationRun) -> dict:
    metrics = getattr(run, 'metric_set', None)
    if metrics is None:
        return {}

    allocation_efficiency = Decimal(metrics.total_pnl) / Decimal(metrics.proposals_generated) if metrics.proposals_generated else Decimal('0')
    return {
        'proposals_generated': metrics.proposals_generated,
        'trades_executed': metrics.trades_executed_count,
        'approvals_required': metrics.approval_required_count,
        'blocked_count': metrics.blocked_count,
        'favorable_review_rate': str(metrics.favorable_review_rate),
        'total_pnl': str(metrics.total_pnl),
        'ending_equity': str(metrics.ending_equity),
        'equity_delta': str(metrics.equity_delta),
        'safety_events_count': metrics.safety_events_count,
        'cooldown_count': metrics.cooldown_count,
        'hard_stop_count': metrics.hard_stop_count,
        'allocation_efficiency': str(allocation_efficiency),
        'block_rate': str(metrics.block_rate),
        'auto_execution_rate': str(metrics.auto_execution_rate),
    }


def _serialize_payload(payload: dict) -> dict:
    serialized = {}
    for key, value in payload.items():
        if hasattr(value, 'isoformat'):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def execute_experiment(*, profile: StrategyProfile, payload: dict) -> ExperimentExecutionResult:
    run_type = payload['run_type']
    run = ExperimentRun.objects.create(
        strategy_profile=profile,
        run_type=run_type,
        status=ExperimentRunStatus.RUNNING,
        started_at=timezone.now(),
        details={'input': _serialize_payload(payload), 'profile_config': profile.config},
    )

    try:
        if run_type == ExperimentRunType.REPLAY:
            now = timezone.now()
            replay_payload = {
                'provider_scope': payload.get('provider_scope') or 'all',
                'source_scope': _scope_to_replay_source(profile.market_scope),
                'start_timestamp': payload.get('start_timestamp') or (now - timedelta(days=7)),
                'end_timestamp': payload.get('end_timestamp') or now,
                'market_limit': profile.config.get('replay', {}).get('market_limit', 8),
                'active_only': payload.get('active_only', True),
                'use_allocation': payload.get('use_allocation', True),
                'use_learning_adjustments': profile.config.get('learning', {}).get('enabled', True),
                'auto_execute_allowed': profile.config.get('replay', {}).get('auto_execute_allowed', True),
                'treat_approval_required_as_skip': profile.config.get('replay', {}).get('treat_approval_required_as_skip', True),
                'stop_on_error': payload.get('stop_on_error', False),
            }
            replay_result = run_replay(config=replay_payload)
            replay_run = replay_result.run
            run.related_replay_run = replay_run
            run.normalized_metrics = _normalize_replay_metrics(replay_run)
            run.status = ExperimentRunStatus.SUCCESS if replay_run.status == 'SUCCESS' else ExperimentRunStatus.PARTIAL
            run.summary = replay_run.summary or f'Replay experiment completed with {replay_run.status}.'

        elif run_type == ExperimentRunType.LIVE_EVAL:
            session_id = payload.get('related_continuous_session_id')
            if session_id:
                session = ContinuousDemoSession.objects.get(pk=session_id)
                eval_run = build_run_for_continuous_session(session)
                run.related_continuous_session = session
            else:
                eval_run = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id').first()
                if eval_run is None:
                    raise ValueError('No evaluation runs available. Run continuous demo or create evaluation data first.')
            run.related_evaluation_run = eval_run
            run.normalized_metrics = _normalize_evaluation_metrics(eval_run)
            run.status = ExperimentRunStatus.SUCCESS
            run.summary = eval_run.summary or 'Live paper evaluation linked to strategy profile.'

        else:
            replay_run = ReplayRun.objects.order_by('-created_at', '-id').first()
            eval_run = EvaluationRun.objects.select_related('metric_set').order_by('-started_at', '-id').first()
            if replay_run:
                run.related_replay_run = replay_run
            if eval_run:
                run.related_evaluation_run = eval_run
            replay_metrics = _normalize_replay_metrics(replay_run) if replay_run else {}
            eval_metrics = _normalize_evaluation_metrics(eval_run) if eval_run else {}
            run.normalized_metrics = {
                'replay': replay_metrics,
                'live_eval': eval_metrics,
                'delta_total_pnl': str(_as_decimal(eval_metrics.get('total_pnl')) - _as_decimal(replay_metrics.get('total_pnl'))),
                'delta_block_rate': str(_as_decimal(eval_metrics.get('block_rate')) - _as_decimal(replay_metrics.get('block_rate'))),
            }
            run.status = ExperimentRunStatus.SUCCESS if replay_run or eval_run else ExperimentRunStatus.FAILED
            run.summary = 'Live-vs-replay comparison snapshot created.' if replay_run or eval_run else 'No replay/evaluation runs available to compare.'

    except Exception as exc:
        run.status = ExperimentRunStatus.FAILED
        run.summary = f'Experiment failed: {exc}'
        run.details = {**(run.details or {}), 'error': str(exc)}
    finally:
        run.finished_at = timezone.now()
        run.save()

    return ExperimentExecutionResult(experiment_run=run)
