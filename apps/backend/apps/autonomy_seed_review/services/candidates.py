from dataclasses import dataclass, field

from apps.autonomy_seed.models import GovernanceSeed
from apps.autonomy_seed_review.services.status import derive_downstream_status, is_ready_for_resolution


@dataclass
class SeedReviewCandidate:
    governance_seed: int
    governance_package: int
    linked_decisions: list[int]
    target_scope: str
    seed_status: str
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def build_seed_review_candidates() -> list[SeedReviewCandidate]:
    rows = (
        GovernanceSeed.objects.select_related('governance_package')
        .order_by('-updated_at', '-id')
    )
    candidates: list[SeedReviewCandidate] = []
    for seed in rows:
        resolution = getattr(seed, 'seed_resolution', None)
        blockers = list(seed.blockers or [])
        status = derive_downstream_status(
            seed_status=seed.seed_status,
            resolution_status=resolution.resolution_status if resolution else None,
            blockers=blockers,
        )
        candidates.append(
            SeedReviewCandidate(
                governance_seed=seed.id,
                governance_package=seed.governance_package_id,
                linked_decisions=list(seed.linked_decisions or []),
                target_scope=seed.target_scope,
                seed_status=seed.seed_status,
                downstream_status=status,
                ready_for_resolution=is_ready_for_resolution(seed_status=seed.seed_status, blockers=blockers),
                blockers=blockers,
                metadata={
                    **(seed.metadata or {}),
                    'resolution_id': resolution.id if resolution else None,
                },
            )
        )
    return candidates
