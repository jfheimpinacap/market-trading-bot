from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.champion_challenger.models import StackProfileBinding
from apps.champion_challenger.services.bindings import get_or_create_champion_binding
from apps.promotion_committee.models import PromotionReviewRun
from apps.rollout_manager.models import StackRolloutPlan, StackRolloutRun, StackRolloutRunStatus

DEFAULT_GUARDRAILS = {
    'min_sample_size': 20,
    'completion_sample_size': 100,
    'min_fill_rate_delta': -0.08,
    'max_no_fill_rate_delta': 0.12,
    'min_execution_adjusted_pnl_delta': -15.0,
    'max_execution_drag_delta': 0.08,
    'max_queue_pressure_delta': 0.20,
    'max_drawdown_delta': 0.03,
}


@transaction.atomic
def create_stack_rollout_plan(*, payload: dict) -> StackRolloutPlan:
    champion_binding = get_or_create_champion_binding()
    candidate_binding_id = payload.get('candidate_binding_id')
    if candidate_binding_id:
        candidate_binding = StackProfileBinding.objects.get(pk=candidate_binding_id)
    elif payload.get('source_review_run_id'):
        review = PromotionReviewRun.objects.select_related('evidence_snapshot__challenger_binding').get(pk=payload['source_review_run_id'])
        if review.evidence_snapshot.challenger_binding is None:
            raise ValueError('Promotion review has no challenger binding to promote.')
        candidate_binding = review.evidence_snapshot.challenger_binding
    else:
        raise ValueError('candidate_binding_id or source_review_run_id is required.')

    if champion_binding.id == candidate_binding.id:
        raise ValueError('Candidate binding must differ from current champion binding.')

    guardrails = {**DEFAULT_GUARDRAILS, **(payload.get('guardrails') or {})}
    canary_percentage = int(payload.get('canary_percentage', 10))

    plan = StackRolloutPlan.objects.create(
        champion_binding=champion_binding,
        candidate_binding=candidate_binding,
        source_review_run_id=payload.get('source_review_run_id'),
        mode=payload.get('mode', 'CANARY'),
        canary_percentage=max(0, min(100, canary_percentage)),
        sampling_rule=payload.get('sampling_rule', 'MARKET_HASH'),
        profile_scope=payload.get('profile_scope', ''),
        guardrails=guardrails,
        summary=payload.get('summary', ''),
        metadata=payload.get('metadata') or {},
    )
    return plan


@transaction.atomic
def start_rollout_run(*, plan: StackRolloutPlan, metadata: dict | None = None) -> StackRolloutRun:
    StackRolloutRun.objects.filter(status__in=[StackRolloutRunStatus.RUNNING, StackRolloutRunStatus.PAUSED]).update(
        status=StackRolloutRunStatus.PAUSED,
        summary='Paused due to a newer rollout run start request.',
    )
    run = StackRolloutRun.objects.create(
        plan=plan,
        status=StackRolloutRunStatus.RUNNING,
        current_phase='CANARY_ACTIVE' if plan.mode != 'SHADOW_ONLY' else 'SHADOW_ACTIVE',
        summary='Rollout run started in paper/demo mode.',
        metadata={**(metadata or {}), 'paper_demo_only': True, 'real_execution_enabled': False},
    )
    return run


@transaction.atomic
def pause_rollout_run(*, run: StackRolloutRun) -> StackRolloutRun:
    run.status = StackRolloutRunStatus.PAUSED
    run.summary = 'Rollout paused by operator action.'
    run.save(update_fields=['status', 'summary', 'updated_at'])
    return run


@transaction.atomic
def resume_rollout_run(*, run: StackRolloutRun) -> StackRolloutRun:
    run.status = StackRolloutRunStatus.RUNNING
    run.summary = 'Rollout resumed by operator action.'
    run.save(update_fields=['status', 'summary', 'updated_at'])
    return run


def get_current_rollout_run() -> StackRolloutRun | None:
    return (
        StackRolloutRun.objects.select_related('plan__champion_binding', 'plan__candidate_binding')
        .filter(status__in=[StackRolloutRunStatus.RUNNING, StackRolloutRunStatus.PAUSED])
        .order_by('-created_at', '-id')
        .first()
    )


def build_rollout_summary() -> dict:
    latest_run = StackRolloutRun.objects.select_related('plan__champion_binding', 'plan__candidate_binding').order_by('-created_at', '-id').first()
    current = get_current_rollout_run()
    return {
        'current_run': current,
        'latest_run': latest_run,
        'total_runs': StackRolloutRun.objects.count(),
        'running_count': StackRolloutRun.objects.filter(status=StackRolloutRunStatus.RUNNING).count(),
        'rolled_back_count': StackRolloutRun.objects.filter(status=StackRolloutRunStatus.ROLLED_BACK).count(),
        'last_updated_at': timezone.now(),
    }
