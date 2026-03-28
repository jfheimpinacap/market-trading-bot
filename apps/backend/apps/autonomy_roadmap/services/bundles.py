from __future__ import annotations

from apps.autonomy_roadmap.models import DomainCriticality, DomainDependency, DomainDependencyType, DomainRoadmapProfile, RoadmapBundle, RoadmapBundleRisk


def build_bundle_payloads(*, dependencies: list[DomainDependency], blocked_domains: list[str]) -> list[dict]:
    profiles = {profile.domain.slug: profile for profile in DomainRoadmapProfile.objects.select_related('domain')}
    payloads: list[dict] = []

    for dependency in dependencies:
        if dependency.dependency_type not in {DomainDependencyType.RECOMMENDED_BEFORE, DomainDependencyType.INCOMPATIBLE_PARALLEL}:
            continue

        source = dependency.source_domain.slug
        target = dependency.target_domain.slug
        name = f'{target}-then-{source}' if dependency.dependency_type == DomainDependencyType.RECOMMENDED_BEFORE else f'{source}-vs-{target}'

        criticality = max(
            [profiles.get(source), profiles.get(target)],
            key=lambda item: [DomainCriticality.LOW, DomainCriticality.MEDIUM, DomainCriticality.HIGH, DomainCriticality.CRITICAL].index(item.criticality if item else DomainCriticality.MEDIUM),
        )
        max_criticality = criticality.criticality if criticality else DomainCriticality.MEDIUM

        risk_level = RoadmapBundleRisk.HIGH if max_criticality in {DomainCriticality.HIGH, DomainCriticality.CRITICAL} else RoadmapBundleRisk.MEDIUM
        requires_approval = risk_level == RoadmapBundleRisk.HIGH or source in blocked_domains or target in blocked_domains

        payloads.append(
            {
                'name': name,
                'domains': [source, target],
                'sequence_order': [target, source] if dependency.dependency_type == DomainDependencyType.RECOMMENDED_BEFORE else [source, target],
                'risk_level': risk_level,
                'requires_approval': requires_approval,
                'rationale': dependency.rationale,
                'metadata': {
                    'dependency_type': dependency.dependency_type,
                    'criticality': max_criticality,
                },
            }
        )

    return payloads


def persist_bundles(*, plan, bundle_payloads: list[dict]) -> list[RoadmapBundle]:
    bundles: list[RoadmapBundle] = []
    for payload in bundle_payloads:
        bundles.append(RoadmapBundle.objects.create(plan=plan, **payload))
    return bundles
