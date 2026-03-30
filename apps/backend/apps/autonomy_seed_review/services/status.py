from apps.autonomy_seed.models import GovernanceSeedStatus
from apps.autonomy_seed_review.models import SeedResolutionStatus


def derive_downstream_status(*, seed_status: str, resolution_status: str | None, blockers: list[str]) -> str:
    if resolution_status:
        return resolution_status
    if blockers:
        return SeedResolutionStatus.BLOCKED
    if seed_status == GovernanceSeedStatus.ACKNOWLEDGED:
        return SeedResolutionStatus.ACKNOWLEDGED
    if seed_status in {GovernanceSeedStatus.READY, GovernanceSeedStatus.REGISTERED}:
        return SeedResolutionStatus.PENDING
    return 'UNKNOWN'


def is_ready_for_resolution(*, seed_status: str, blockers: list[str]) -> bool:
    return seed_status in {GovernanceSeedStatus.READY, GovernanceSeedStatus.REGISTERED, GovernanceSeedStatus.ACKNOWLEDGED} and not blockers
