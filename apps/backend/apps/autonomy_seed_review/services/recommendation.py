from apps.autonomy_seed_review.models import SeedResolutionStatus, SeedReviewRecommendationType


def build_seed_review_recommendations(*, candidate: dict, pending_count: int) -> list[dict]:
    blockers = candidate.get('blockers') or []
    downstream_status = candidate.get('downstream_status')
    payload: list[dict] = []

    if blockers:
        payload.append(
            {
                'recommendation_type': SeedReviewRecommendationType.REQUIRE_MANUAL_SEED_REVIEW,
                'rationale': 'Seed has blockers and requires manual review before resolution.',
                'reason_codes': ['seed_blocked'],
                'confidence': 0.92,
                'blockers': blockers,
                'metadata': {'downstream_status': downstream_status},
            }
        )
    elif downstream_status == SeedResolutionStatus.ACKNOWLEDGED:
        payload.append(
            {
                'recommendation_type': SeedReviewRecommendationType.MARK_SEED_ACCEPTED,
                'rationale': 'Acknowledged seed can be manually promoted to accepted next-cycle input.',
                'reason_codes': ['seed_acknowledged'],
                'confidence': 0.86,
                'blockers': [],
                'metadata': {'downstream_status': downstream_status},
            }
        )
    elif downstream_status in {SeedResolutionStatus.ACCEPTED, SeedResolutionStatus.CLOSED}:
        payload.append(
            {
                'recommendation_type': SeedReviewRecommendationType.KEEP_SEED_PENDING,
                'rationale': 'Seed loop already resolved; keep historical state without duplicating closure.',
                'reason_codes': ['already_resolved'],
                'confidence': 0.9,
                'blockers': [],
                'metadata': {'downstream_status': downstream_status},
            }
        )
    else:
        payload.append(
            {
                'recommendation_type': SeedReviewRecommendationType.ACKNOWLEDGE_SEED,
                'rationale': 'Registered seed should be acknowledged before acceptance/defer/reject.',
                'reason_codes': ['awaiting_manual_ack'],
                'confidence': 0.82,
                'blockers': [],
                'metadata': {'downstream_status': downstream_status},
            }
        )

    if pending_count > 1:
        payload.append(
            {
                'recommendation_type': SeedReviewRecommendationType.REORDER_SEED_REVIEW_PRIORITY,
                'rationale': 'Multiple pending seeds detected; reorder queue to reduce unresolved carryover.',
                'reason_codes': ['pending_queue_pressure'],
                'confidence': 0.71,
                'blockers': [],
                'metadata': {'pending_count': pending_count},
            }
        )
    return payload
