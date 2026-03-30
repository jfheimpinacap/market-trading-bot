from __future__ import annotations

from typing import Iterable

from apps.certification_board.models import (
    BaselineBindingResolutionStatus,
    BaselineConfirmationCandidate,
    BaselineConfirmationRun,
    CertificationCandidate,
    CertificationDecision,
    CertificationDecisionStatus,
    RolloutCertificationRun,
    StabilizationReadiness,
)
from apps.certification_board.services.binding_resolution import resolve_baseline_bindings
from apps.promotion_committee.models import (
    PostRolloutStatus,
    PostRolloutStatusType,
    RolloutExecutionRecord,
    RolloutExecutionStatus,
)

_TERMINAL_EXECUTION_STATUSES: tuple[str, ...] = (
    RolloutExecutionStatus.EXECUTED,
    RolloutExecutionStatus.FAILED,
    RolloutExecutionStatus.ROLLBACK_RECOMMENDED,
    RolloutExecutionStatus.REVERTED,
)


def _derive_readiness(*, execution: RolloutExecutionRecord, post_status: PostRolloutStatus | None, blockers: list[str]) -> str:
    if execution.execution_status in {RolloutExecutionStatus.FAILED, RolloutExecutionStatus.REVERTED}:
        return StabilizationReadiness.ROLLBACK_RECOMMENDED

    if post_status and post_status.status in {PostRolloutStatusType.ROLLBACK_RECOMMENDED, PostRolloutStatusType.REVERTED}:
        return StabilizationReadiness.ROLLBACK_RECOMMENDED

    if blockers:
        return StabilizationReadiness.BLOCKED

    if post_status is None or post_status.status == PostRolloutStatusType.INCOMPLETE:
        return StabilizationReadiness.NEEDS_OBSERVATION

    if post_status.status == PostRolloutStatusType.REVIEW_REQUIRED:
        return StabilizationReadiness.REVIEW_REQUIRED

    if post_status.status == PostRolloutStatusType.CAUTION:
        return StabilizationReadiness.NEEDS_OBSERVATION

    if post_status.status == PostRolloutStatusType.HEALTHY and execution.execution_status == RolloutExecutionStatus.EXECUTED:
        return StabilizationReadiness.READY

    return StabilizationReadiness.NEEDS_OBSERVATION


def build_rollout_certification_candidates(
    *,
    review_run: RolloutCertificationRun,
    rollout_execution_run_id: int | None = None,
) -> list[CertificationCandidate]:
    executions = (
        RolloutExecutionRecord.objects.select_related(
            'linked_rollout_plan',
            'linked_rollout_plan__linked_candidate',
            'linked_rollout_plan__linked_candidate__linked_promotion_case',
            'execution_run',
        )
        .prefetch_related('post_rollout_statuses')
        .filter(execution_status__in=_TERMINAL_EXECUTION_STATUSES)
        .order_by('-created_at', '-id')
    )

    if rollout_execution_run_id:
        executions = executions.filter(execution_run_id=rollout_execution_run_id)

    candidates: list[CertificationCandidate] = []
    for execution in executions:
        post_status = execution.post_rollout_statuses.order_by('-created_at', '-id').first()
        blockers = list(execution.blockers or [])
        if not post_status:
            blockers.append('missing_post_rollout_status')

        readiness = _derive_readiness(execution=execution, post_status=post_status, blockers=blockers)
        promotion_case = getattr(getattr(execution.linked_rollout_plan, 'linked_candidate', None), 'linked_promotion_case', None)
        candidate = CertificationCandidate.objects.create(
            review_run=review_run,
            linked_rollout_execution=execution,
            linked_post_rollout_status=post_status,
            linked_rollout_plan=execution.linked_rollout_plan,
            linked_promotion_case=promotion_case,
            target_component=execution.linked_rollout_plan.target_component,
            target_scope=execution.linked_rollout_plan.target_scope,
            rollout_status=execution.execution_status,
            stabilization_readiness=readiness,
            blockers=blockers,
            metadata={
                'execution_run_id': execution.execution_run_id,
                'promotion_case_id': promotion_case.id if promotion_case else None,
                'post_rollout_status_id': post_status.id if post_status else None,
                'trace_chain': {
                    'tuning_proposal_id': promotion_case.linked_tuning_proposal_id if promotion_case else None,
                    'experiment_candidate_id': promotion_case.linked_experiment_candidate_id if promotion_case else None,
                    'promotion_case_id': promotion_case.id if promotion_case else None,
                    'manual_rollout_plan_id': execution.linked_rollout_plan_id,
                    'rollout_execution_id': execution.id,
                },
            },
        )
        candidates.append(candidate)

    return candidates


def build_baseline_confirmation_candidates(*, review_run: BaselineConfirmationRun) -> list[BaselineConfirmationCandidate]:
    decisions = CertificationDecision.objects.select_related(
        'linked_candidate',
        'linked_candidate__linked_rollout_execution',
        'linked_candidate__linked_promotion_case',
    ).filter(decision_status=CertificationDecisionStatus.CERTIFIED_FOR_PAPER_BASELINE)

    candidates: list[BaselineConfirmationCandidate] = []
    for decision in decisions.order_by('-created_at', '-id'):
        if BaselineConfirmationCandidate.objects.filter(linked_certification_decision=decision).exists():
            continue

        resolved = resolve_baseline_bindings(decision=decision)
        ready = resolved.binding_resolution_status == BaselineBindingResolutionStatus.RESOLVED

        candidate = BaselineConfirmationCandidate.objects.create(
            review_run=review_run,
            linked_certification_decision=decision,
            linked_certification_candidate=decision.linked_candidate,
            linked_rollout_execution=decision.linked_candidate.linked_rollout_execution,
            target_component=decision.linked_candidate.target_component,
            target_scope=decision.linked_candidate.target_scope,
            certification_status=decision.decision_status,
            previous_baseline_reference=resolved.previous_baseline_reference,
            proposed_baseline_reference=resolved.proposed_baseline_reference,
            binding_resolution_status=resolved.binding_resolution_status,
            ready_for_confirmation=ready,
            blockers=resolved.blockers,
            metadata={
                'binding_snapshot': resolved.snapshot,
                'decision_id': decision.id,
                'certification_candidate_id': decision.linked_candidate_id,
            },
        )
        candidates.append(candidate)

    return candidates


def summarize_readiness(candidates: Iterable[CertificationCandidate]) -> dict[str, int]:
    rows = list(candidates)
    return {
        'ready': sum(1 for item in rows if item.stabilization_readiness == StabilizationReadiness.READY),
        'needs_observation': sum(
            1 for item in rows if item.stabilization_readiness == StabilizationReadiness.NEEDS_OBSERVATION
        ),
        'review_required': sum(1 for item in rows if item.stabilization_readiness == StabilizationReadiness.REVIEW_REQUIRED),
        'rollback_recommended': sum(
            1 for item in rows if item.stabilization_readiness == StabilizationReadiness.ROLLBACK_RECOMMENDED
        ),
        'blocked': sum(1 for item in rows if item.stabilization_readiness == StabilizationReadiness.BLOCKED),
    }


def build_baseline_activation_candidates(*, review_run):
    from apps.certification_board.models import (
        BaselineActivationCandidate,
        BaselineBindingResolutionStatus,
        PaperBaselineConfirmation,
        PaperBaselineConfirmationStatus,
    )
    from apps.certification_board.services.binding_resolution import resolve_activation_bindings

    confirmations = PaperBaselineConfirmation.objects.select_related('linked_candidate', 'linked_certification_decision').filter(
        confirmation_status=PaperBaselineConfirmationStatus.CONFIRMED
    ).order_by('-confirmed_at', '-id')

    created: list[BaselineActivationCandidate] = []
    for confirmation in confirmations:
        if BaselineActivationCandidate.objects.filter(review_run=review_run, linked_paper_baseline_confirmation=confirmation).exists():
            continue

        resolved = resolve_activation_bindings(confirmation=confirmation)
        ready = resolved.activation_resolution_status == BaselineBindingResolutionStatus.RESOLVED

        candidate = BaselineActivationCandidate.objects.create(
            review_run=review_run,
            linked_paper_baseline_confirmation=confirmation,
            linked_certification_decision=confirmation.linked_certification_decision,
            target_component=confirmation.target_component,
            target_scope=confirmation.target_scope,
            previous_active_reference=resolved.previous_active_reference,
            proposed_active_reference=resolved.proposed_active_reference,
            activation_resolution_status=resolved.activation_resolution_status,
            ready_for_activation=ready,
            blockers=resolved.blockers,
            metadata={
                'binding_snapshot': resolved.snapshot,
                'paper_baseline_confirmation_id': confirmation.id,
                'baseline_confirmation_candidate_id': confirmation.linked_candidate_id,
            },
        )
        created.append(candidate)

    return created
