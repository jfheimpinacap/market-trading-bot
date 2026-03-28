from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.autonomy_roadmap.models import DomainDependencyType


@dataclass
class ScenarioRiskDraft:
    dependency_conflict_risk: Decimal
    approval_friction_risk: Decimal
    degraded_posture_risk: Decimal
    incident_exposure_risk: Decimal
    rollback_likelihood_hint: Decimal
    bundle_risk_level: str
    confidence: Decimal
    approval_heavy: bool
    conflicts: list[dict]
    blockers: list[str]
    metadata: dict


def estimate_option_risk(*, option, evidence: dict, dependencies: list) -> ScenarioRiskDraft:
    rows_by_slug = {row['domain_slug']: row for row in evidence.get('domains', [])}
    approval = evidence.get('approval', {})
    incidents = evidence.get('incidents', {})
    trust = evidence.get('trust_calibration', {})

    conflicts: list[dict] = []
    blockers: set[str] = set()
    dependency_conflict_risk = Decimal('0.1200')

    for dependency in dependencies:
        if dependency.source_domain.slug not in option.domains:
            continue
        target_slug = dependency.target_domain.slug
        target = rows_by_slug.get(target_slug)
        if not target:
            continue

        if dependency.dependency_type == DomainDependencyType.REQUIRES_STABLE and (target['under_observation'] or target['is_degraded']):
            dependency_conflict_risk += Decimal('0.3500')
            blockers.add(f'{dependency.source_domain.slug} requires stable {target_slug}')
            conflicts.append({'type': 'REQUIRES_STABLE', 'source': dependency.source_domain.slug, 'target': target_slug})

        if dependency.dependency_type == DomainDependencyType.BLOCKS_IF_DEGRADED and target['is_degraded']:
            dependency_conflict_risk += Decimal('0.2800')
            blockers.add(f'{dependency.source_domain.slug} blocked while {target_slug} degraded')
            conflicts.append({'type': 'BLOCKS_IF_DEGRADED', 'source': dependency.source_domain.slug, 'target': target_slug})

        if dependency.dependency_type == DomainDependencyType.INCOMPATIBLE_PARALLEL and option.is_bundle and target_slug in option.domains:
            dependency_conflict_risk += Decimal('0.3200')
            blockers.add(f'Parallel incompatibility {dependency.source_domain.slug} vs {target_slug}')
            conflicts.append({'type': 'INCOMPATIBLE_PARALLEL', 'source': dependency.source_domain.slug, 'target': target_slug})

    degraded_count = sum(1 for slug in option.domains if rows_by_slug.get(slug, {}).get('is_degraded'))
    observing_count = sum(1 for slug in option.domains if rows_by_slug.get(slug, {}).get('under_observation'))

    degraded_posture_risk = Decimal('0.1000') + Decimal(degraded_count) * Decimal('0.2800') + Decimal(observing_count) * Decimal('0.1400')
    incident_exposure_risk = Decimal('0.0800') + Decimal(str(min(0.7, ((incidents.get('critical_active', 0) * 0.18) + (incidents.get('high_active', 0) * 0.08)))))
    approval_friction_risk = Decimal('0.0900') + Decimal(str(min(0.8, (approval.get('high_priority_pending', 0) * 0.03) + (float(trust.get('avg_approval_friction', '0')) * 0.5))))

    if option.is_bundle:
        approval_friction_risk += Decimal('0.1000')
        incident_exposure_risk += Decimal('0.0500')

    rollback_likelihood_hint = (dependency_conflict_risk + degraded_posture_risk + incident_exposure_risk) / Decimal('3')
    approval_heavy = approval_friction_risk >= Decimal('0.4500') or option.is_bundle and dependency_conflict_risk >= Decimal('0.3500')

    total_risk = float(dependency_conflict_risk + degraded_posture_risk + incident_exposure_risk)
    if total_risk >= 1.4:
        bundle_risk_level = 'HIGH'
    elif total_risk >= 0.9:
        bundle_risk_level = 'MEDIUM'
    else:
        bundle_risk_level = 'LOW'

    confidence = Decimal('0.7000')
    if blockers:
        confidence = Decimal('0.8700')
    elif option.option_type == 'DELAY_UNTIL_STABLE':
        confidence = Decimal('0.8300')

    return ScenarioRiskDraft(
        dependency_conflict_risk=min(dependency_conflict_risk, Decimal('0.9900')),
        approval_friction_risk=min(approval_friction_risk, Decimal('0.9900')),
        degraded_posture_risk=min(degraded_posture_risk, Decimal('0.9900')),
        incident_exposure_risk=min(incident_exposure_risk, Decimal('0.9900')),
        rollback_likelihood_hint=min(rollback_likelihood_hint, Decimal('0.9900')),
        bundle_risk_level=bundle_risk_level,
        confidence=confidence,
        approval_heavy=approval_heavy,
        conflicts=conflicts,
        blockers=sorted(blockers),
        metadata={'manual_first': True, 'simulation_only': True},
    )
