from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.champion_challenger.models import ChampionChallengerRun, ChampionChallengerRunStatus, ShadowComparisonResult
from apps.champion_challenger.services.bindings import create_challenger_binding, get_or_create_champion_binding
from apps.champion_challenger.services.comparison import compare_metrics, normalize_replay_metrics
from apps.champion_challenger.services.recommendation import generate_recommendation
from apps.replay_lab.services import run_replay
from apps.replay_lab.services.execution_replay import REPLAY_EXECUTION_MODE_AWARE


def _replay_config(*, execution_profile: str, provider_scope: str, source_scope: str, start_timestamp, end_timestamp) -> dict:
    return {
        'provider_scope': provider_scope,
        'source_scope': source_scope,
        'start_timestamp': start_timestamp,
        'end_timestamp': end_timestamp,
        'active_only': True,
        'use_allocation': True,
        'use_learning_adjustments': True,
        'auto_execute_allowed': True,
        'treat_approval_required_as_skip': True,
        'stop_on_error': False,
        'execution_mode': REPLAY_EXECUTION_MODE_AWARE,
        'execution_profile': execution_profile,
    }


def run_shadow_benchmark(*, payload: dict) -> ChampionChallengerRun:
    champion = get_or_create_champion_binding()
    challenger = create_challenger_binding(name=payload.get('challenger_name') or 'challenger_shadow', overrides=payload.get('challenger_overrides'))

    end_timestamp = payload.get('end_timestamp') or timezone.now()
    start_timestamp = payload.get('start_timestamp') or (end_timestamp - timedelta(hours=int(payload.get('lookback_hours') or 24)))
    provider_scope = payload.get('provider_scope') or 'all'
    source_scope = payload.get('source_scope') or 'mixed'

    run = ChampionChallengerRun.objects.create(
        champion_binding=champion,
        challenger_binding=challenger,
        status=ChampionChallengerRunStatus.RUNNING,
        started_at=timezone.now(),
        details={
            'mode': 'shadow_paper_benchmark',
            'paper_demo_only': True,
            'real_execution_enabled': False,
            'input': {
                'provider_scope': provider_scope,
                'source_scope': source_scope,
                'start_timestamp': start_timestamp.isoformat(),
                'end_timestamp': end_timestamp.isoformat(),
            },
        },
    )

    try:
        champion_replay = run_replay(
            config=_replay_config(
                execution_profile=champion.execution_profile,
                provider_scope=provider_scope,
                source_scope=source_scope,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
        ).run
        challenger_replay = run_replay(
            config=_replay_config(
                execution_profile=challenger.execution_profile,
                provider_scope=provider_scope,
                source_scope=source_scope,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
        ).run

        champion_metrics = normalize_replay_metrics(champion_replay)
        challenger_metrics = normalize_replay_metrics(challenger_replay)
        comparison = compare_metrics(champion=champion_metrics, challenger=challenger_metrics)
        code, reasons = generate_recommendation(comparison=comparison)

        ShadowComparisonResult.objects.create(
            run=run,
            champion_metrics=champion_metrics,
            challenger_metrics=challenger_metrics,
            deltas=comparison['deltas'],
            decision_divergence_rate=Decimal(str(comparison['decision_divergence_rate'])),
        )

        run.markets_evaluated = max(champion_metrics['markets_evaluated'], challenger_metrics['markets_evaluated'])
        run.opportunities_compared = max(champion_metrics['opportunity_count'], challenger_metrics['opportunity_count'])
        run.proposals_compared = max(champion_metrics['proposal_ready_count'], challenger_metrics['proposal_ready_count'])
        run.fills_compared = max(champion_metrics['fill_count'], challenger_metrics['fill_count'])
        run.pnl_delta_execution_adjusted = Decimal(str(comparison['deltas']['execution_adjusted_pnl_delta']))
        run.recommendation_code = code
        run.recommendation_reasons = reasons
        run.status = ChampionChallengerRunStatus.COMPLETED
        run.summary = f"Shadow benchmark completed. Recommendation: {code}."
        run.details = {
            **(run.details or {}),
            'champion_replay_run_id': champion_replay.id,
            'challenger_replay_run_id': challenger_replay.id,
            'comparison': comparison,
            'inputs': {
                'prediction_model_champion_id': champion.prediction_model_artifact_id,
                'prediction_model_challenger_id': challenger.prediction_model_artifact_id,
                'prediction_profile_champion': champion.prediction_profile_slug,
                'prediction_profile_challenger': challenger.prediction_profile_slug,
            },
        }
    except Exception as exc:
        run.status = ChampionChallengerRunStatus.FAILED
        run.summary = f'Shadow benchmark failed: {exc}'
        run.details = {**(run.details or {}), 'error': str(exc)}
    finally:
        run.finished_at = timezone.now()
        run.save()

    return run
