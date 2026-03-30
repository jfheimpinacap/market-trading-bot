from django.utils import timezone

from apps.autonomy_seed_review.models import SeedResolution, SeedResolutionStatus, SeedResolutionType


def _resolution_type_for_scope(scope: str) -> str:
    mapping = {
        'roadmap': SeedResolutionType.ROADMAP_SEED_ACKNOWLEDGED,
        'scenario': SeedResolutionType.SCENARIO_SEED_ACKNOWLEDGED,
        'program': SeedResolutionType.PROGRAM_SEED_ACKNOWLEDGED,
        'manager': SeedResolutionType.MANAGER_SEED_ACKNOWLEDGED,
        'operator_review': SeedResolutionType.OPERATOR_SEED_ACKNOWLEDGED,
    }
    return mapping.get(scope, SeedResolutionType.MANUAL_REVIEW_REQUIRED)


def _upsert_resolution(*, seed, status: str, actor: str, rationale: str, reason_codes: list[str]) -> SeedResolution:
    resolution, _ = SeedResolution.objects.get_or_create(
        governance_seed=seed,
        defaults={
            'resolution_status': status,
            'resolution_type': _resolution_type_for_scope(seed.target_scope),
            'rationale': rationale,
            'reason_codes': reason_codes,
            'blockers': list(seed.blockers or []),
            'resolved_by': actor,
            'resolved_at': timezone.now(),
            'linked_target_artifact': seed.linked_target_artifact,
            'metadata': {'actor': actor, 'source': 'autonomy_seed_review'},
        },
    )
    if resolution.resolution_status in {SeedResolutionStatus.ACCEPTED, SeedResolutionStatus.CLOSED} and status in {SeedResolutionStatus.ACCEPTED, SeedResolutionStatus.CLOSED}:
        return resolution
    resolution.resolution_status = status
    resolution.resolution_type = _resolution_type_for_scope(seed.target_scope)
    resolution.rationale = rationale
    resolution.reason_codes = reason_codes
    resolution.blockers = list(seed.blockers or [])
    resolution.resolved_by = actor
    resolution.resolved_at = timezone.now()
    resolution.linked_target_artifact = seed.linked_target_artifact
    resolution.metadata = {**(resolution.metadata or {}), 'actor': actor, 'source': 'autonomy_seed_review'}
    resolution.save()
    return resolution


def acknowledge_seed(*, seed, actor: str) -> SeedResolution:
    return _upsert_resolution(
        seed=seed,
        status=SeedResolutionStatus.ACKNOWLEDGED,
        actor=actor,
        rationale='Seed acknowledged for manual next-cycle planning review.',
        reason_codes=['manual_acknowledged'],
    )


def mark_seed_accepted(*, seed, actor: str) -> SeedResolution:
    return _upsert_resolution(
        seed=seed,
        status=SeedResolutionStatus.ACCEPTED,
        actor=actor,
        rationale='Seed accepted as an input for the next planning cycle.',
        reason_codes=['accepted_for_next_cycle'],
    )


def mark_seed_deferred(*, seed, actor: str) -> SeedResolution:
    return _upsert_resolution(
        seed=seed,
        status=SeedResolutionStatus.DEFERRED,
        actor=actor,
        rationale='Seed deferred pending future context or capacity.',
        reason_codes=['deferred_by_operator'],
    )


def mark_seed_rejected(*, seed, actor: str) -> SeedResolution:
    return _upsert_resolution(
        seed=seed,
        status=SeedResolutionStatus.REJECTED,
        actor=actor,
        rationale='Seed rejected after manual review.',
        reason_codes=['rejected_by_operator'],
    )
