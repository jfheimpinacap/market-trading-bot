from apps.promotion_committee.models import PromotionReviewRun


def get_current_recommendation() -> PromotionReviewRun | None:
    return PromotionReviewRun.objects.select_related('evidence_snapshot__champion_binding', 'evidence_snapshot__challenger_binding').prefetch_related('decision_logs').order_by('-created_at', '-id').first()


def build_promotion_summary() -> dict:
    runs = PromotionReviewRun.objects.order_by('-created_at', '-id')
    latest = runs.first()
    total = runs.count()
    by_code = {}
    for code in ['KEEP_CURRENT_CHAMPION', 'PROMOTE_CHALLENGER', 'EXTEND_SHADOW_TEST', 'REVERT_TO_CONSERVATIVE_STACK', 'MANUAL_REVIEW_REQUIRED']:
        by_code[code] = runs.filter(recommendation_code=code).count()

    stale = False
    if latest is not None:
        stale = (latest.created_at.timestamp() < (__import__('time').time() - 60 * 60 * 24 * 3))

    return {
        'latest_run': latest,
        'total_runs': total,
        'recommendation_counts': by_code,
        'is_recommendation_stale': stale,
    }
