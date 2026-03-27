from apps.promotion_committee.models import PromotionDecisionLog, PromotionDecisionMode, PromotionReviewRun, PromotionReviewRunStatus
from apps.promotion_committee.services.evidence import build_stack_evidence_snapshot
from apps.promotion_committee.services.recommendation import generate_recommendation


def run_promotion_review(*, challenger_binding_id: int | None = None, decision_mode: str = PromotionDecisionMode.RECOMMENDATION_ONLY, metadata: dict | None = None) -> PromotionReviewRun:
    snapshot = build_stack_evidence_snapshot(challenger_binding_id=challenger_binding_id, metadata=metadata)
    recommendation = generate_recommendation(snapshot)

    run = PromotionReviewRun.objects.create(
        status=PromotionReviewRunStatus.COMPLETED,
        decision_mode=decision_mode,
        readiness_status=snapshot.readiness_summary.get('status', ''),
        evidence_snapshot=snapshot,
        recommendation_code=recommendation.code,
        confidence=recommendation.confidence,
        rationale=recommendation.rationale,
        reason_codes=recommendation.reason_codes,
        blocking_constraints=recommendation.blocking_constraints,
        evidence_summary=recommendation.evidence_summary,
        summary=f"{recommendation.code}: {recommendation.rationale}",
        metadata=metadata or {},
    )
    PromotionDecisionLog.objects.create(
        review_run=run,
        event_type='RECOMMENDATION_ISSUED',
        actor='promotion_committee',
        notes='Promotion recommendation generated from consolidated stack evidence.',
        payload={
            'recommendation_code': recommendation.code,
            'reason_codes': recommendation.reason_codes,
            'blocking_constraints': recommendation.blocking_constraints,
        },
    )
    return run
