from __future__ import annotations

from apps.autonomy_manager.models import AutonomyDomain
from apps.autonomy_manager.services.domains import sync_domain_catalog
from apps.autonomy_roadmap.models import DomainDependency, DomainDependencyType, DomainRoadmapProfile, DomainCriticality


DEPENDENCY_SEEDS = [
    {
        'source': 'runbook_remediation',
        'target': 'incident_response',
        'dependency_type': DomainDependencyType.REQUIRES_STABLE,
        'rationale': 'Runbook automation should not advance while incident response is unstable.',
    },
    {
        'source': 'rollout_controls',
        'target': 'certification_reviews',
        'dependency_type': DomainDependencyType.RECOMMENDED_BEFORE,
        'rationale': 'Rollout controls should mature after certification review maturity is established.',
    },
    {
        'source': 'venue_reconciliation',
        'target': 'bridge_validation_review',
        'dependency_type': DomainDependencyType.REQUIRES_STABLE,
        'rationale': 'Venue reconciliation autonomy depends on reliable bridge validation posture.',
    },
    {
        'source': 'profile_governance_actions',
        'target': 'incident_response',
        'dependency_type': DomainDependencyType.BLOCKS_IF_DEGRADED,
        'rationale': 'Profile governance promotions are blocked when incident posture is degraded.',
    },
    {
        'source': 'profile_governance_actions',
        'target': 'portfolio_governance_actions',
        'dependency_type': DomainDependencyType.INCOMPATIBLE_PARALLEL,
        'rationale': 'Avoid simultaneous promotions of profile and portfolio governance due to coupled risk.',
    },
]


CRITICALITY_SEEDS = {
    'incident_response': DomainCriticality.CRITICAL,
    'runbook_remediation': DomainCriticality.HIGH,
    'certification_reviews': DomainCriticality.HIGH,
    'rollout_controls': DomainCriticality.HIGH,
    'profile_governance_actions': DomainCriticality.HIGH,
    'portfolio_governance_actions': DomainCriticality.HIGH,
    'venue_reconciliation': DomainCriticality.MEDIUM,
    'bridge_validation_review': DomainCriticality.MEDIUM,
}


def seed_dependencies() -> list[DomainDependency]:
    sync_domain_catalog()
    by_slug = {domain.slug: domain for domain in AutonomyDomain.objects.all()}
    records: list[DomainDependency] = []
    for seed in DEPENDENCY_SEEDS:
        source = by_slug.get(seed['source'])
        target = by_slug.get(seed['target'])
        if not source or not target:
            continue
        row, _ = DomainDependency.objects.update_or_create(
            source_domain=source,
            target_domain=target,
            dependency_type=seed['dependency_type'],
            defaults={
                'rationale': seed['rationale'],
                'metadata': {'seeded': True},
            },
        )
        records.append(row)

    for domain in AutonomyDomain.objects.all():
        DomainRoadmapProfile.objects.update_or_create(
            domain=domain,
            defaults={
                'criticality': CRITICALITY_SEEDS.get(domain.slug, DomainCriticality.MEDIUM),
                'metadata': {'seeded': True},
            },
        )

    return records


def list_dependencies() -> list[DomainDependency]:
    seed_dependencies()
    return list(DomainDependency.objects.select_related('source_domain', 'target_domain').order_by('source_domain__slug', 'target_domain__slug', 'dependency_type'))
