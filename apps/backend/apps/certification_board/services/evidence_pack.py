from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import CertificationCandidate, CertificationEvidencePack, CertificationEvidenceStatus
from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRunStatus
from apps.promotion_committee.models import CheckpointOutcomeStatus, CheckpointTriggeredAction, PostRolloutStatusType


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(max(0.0, min(1.0, value))))


def _derive_evidence_status(*, sample_count: int, confidence_score: Decimal, stability_score: Decimal, regression_risk_score: Decimal) -> str:
    if sample_count < 2:
        return CertificationEvidenceStatus.INSUFFICIENT
    if confidence_score >= Decimal('0.75') and stability_score >= Decimal('0.75') and regression_risk_score <= Decimal('0.30'):
        return CertificationEvidenceStatus.STRONG
    if confidence_score >= Decimal('0.60') and stability_score >= Decimal('0.55') and regression_risk_score <= Decimal('0.45'):
        return CertificationEvidenceStatus.MIXED
    return CertificationEvidenceStatus.WEAK


def build_certification_evidence_pack(*, candidate: CertificationCandidate) -> CertificationEvidencePack:
    execution = candidate.linked_rollout_execution
    outcomes = list(execution.checkpoint_outcomes.select_related('linked_checkpoint_plan').order_by('-created_at', '-id'))
    statuses = list(execution.post_rollout_statuses.order_by('-created_at', '-id')[:3])

    pass_count = sum(1 for row in outcomes if row.outcome_status == CheckpointOutcomeStatus.PASSED)
    warning_count = sum(1 for row in outcomes if row.outcome_status == CheckpointOutcomeStatus.WARNING)
    failed_count = sum(1 for row in outcomes if row.outcome_status == CheckpointOutcomeStatus.FAILED)
    rollback_trigger_count = sum(1 for row in outcomes if row.triggered_action == CheckpointTriggeredAction.RECOMMEND_ROLLBACK)

    latest_status = statuses[0].status if statuses else None
    status_penalty = Decimal('0.00')
    if latest_status == PostRolloutStatusType.CAUTION:
        status_penalty = Decimal('0.10')
    elif latest_status == PostRolloutStatusType.REVIEW_REQUIRED:
        status_penalty = Decimal('0.25')
    elif latest_status in {PostRolloutStatusType.ROLLBACK_RECOMMENDED, PostRolloutStatusType.REVERTED}:
        status_penalty = Decimal('0.45')

    sample_count = len(outcomes) + len(statuses)
    confidence_raw = 0.0 if sample_count == 0 else (pass_count + (0.5 * warning_count)) / max(len(outcomes), 1)
    stability_raw = 0.0 if sample_count == 0 else max(0.0, 1.0 - ((failed_count + rollback_trigger_count) / max(sample_count, 1)))
    regression_raw = min(1.0, (failed_count * 0.35) + (rollback_trigger_count * 0.30) + float(status_penalty))

    confidence_score = max(_to_decimal(confidence_raw) - status_penalty, Decimal('0.0000'))
    stability_score = max(_to_decimal(stability_raw) - (status_penalty / Decimal('2')), Decimal('0.0000'))
    regression_risk_score = _to_decimal(regression_raw)

    latest_eval = (
        EvaluationMetricSet.objects.select_related('run')
        .filter(run__status=EvaluationRunStatus.READY)
        .order_by('-created_at', '-id')
        .first()
    )

    evaluation_metrics = {
        'evaluation_run_id': latest_eval.run_id if latest_eval else None,
        'favorable_review_rate': str(latest_eval.favorable_review_rate) if latest_eval else None,
        'hard_stop_count': latest_eval.hard_stop_count if latest_eval else None,
        'safety_events_count': latest_eval.safety_events_count if latest_eval else None,
    }

    evidence_status = _derive_evidence_status(
        sample_count=sample_count,
        confidence_score=confidence_score,
        stability_score=stability_score,
        regression_risk_score=regression_risk_score,
    )

    return CertificationEvidencePack.objects.create(
        linked_candidate=candidate,
        summary=f"Post-rollout evidence for execution #{execution.id} ({pass_count} passed, {warning_count} warning, {failed_count} failed checkpoints).",
        linked_checkpoint_outcomes=[
            {
                'id': row.id,
                'checkpoint_plan_id': row.linked_checkpoint_plan_id,
                'checkpoint_type': row.linked_checkpoint_plan.checkpoint_type,
                'outcome_status': row.outcome_status,
                'triggered_action': row.triggered_action,
            }
            for row in outcomes
        ],
        linked_post_rollout_statuses=[
            {
                'id': row.id,
                'status': row.status,
                'status_rationale': row.status_rationale,
                'observed_drift_flags': row.observed_drift_flags,
                'observed_risk_flags': row.observed_risk_flags,
                'observed_calibration_flags': row.observed_calibration_flags,
            }
            for row in statuses
        ],
        linked_evaluation_metrics=evaluation_metrics,
        sample_count=sample_count,
        confidence_score=confidence_score,
        stability_score=stability_score,
        regression_risk_score=regression_risk_score,
        evidence_status=evidence_status,
        metadata={
            'checkpoint_counts': {
                'passed': pass_count,
                'warning': warning_count,
                'failed': failed_count,
            },
            'rollback_trigger_count': rollback_trigger_count,
        },
    )
