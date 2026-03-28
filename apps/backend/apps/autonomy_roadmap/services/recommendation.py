from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.autonomy_manager.models import AutonomyDomain, AutonomyStage
from apps.autonomy_roadmap.models import (
    DomainDependency,
    DomainDependencyType,
    DomainRoadmapProfile,
    RoadmapRecommendation,
    RoadmapRecommendationAction,
)


@dataclass
class RecommendationDraft:
    domain: AutonomyDomain
    action: str
    current_stage: str
    proposed_stage: str
    rationale: str
    reason_codes: list[str]
    confidence: Decimal
    evidence_refs: list[dict]


def _next_stage(current_stage: str) -> str:
    if current_stage == AutonomyStage.MANUAL:
        return AutonomyStage.ASSISTED
    if current_stage == AutonomyStage.ASSISTED:
        return AutonomyStage.SUPERVISED_AUTOPILOT
    return current_stage


def build_recommendation_drafts(*, evidence: dict, dependencies: list[DomainDependency]) -> tuple[list[RecommendationDraft], dict]:
    by_slug = {row['domain_slug']: row for row in evidence['domains']}
    domains_by_slug = {domain.slug: domain for domain in AutonomyDomain.objects.all()}
    profiles = {profile.domain.slug: profile for profile in DomainRoadmapProfile.objects.select_related('domain')}

    blocked_domains: set[str] = set()
    frozen_domains: set[str] = set()
    drafts: list[RecommendationDraft] = []

    for row in evidence['domains']:
        slug = row['domain_slug']
        current_stage = row['current_stage']
        proposed_stage = _next_stage(current_stage)
        action = RoadmapRecommendationAction.PROMOTE_DOMAIN
        reason_codes = ['ROADMAP_READY']
        evidence_refs = [
            {'type': 'autonomy_stage_state', 'domain': slug},
        ]
        confidence = Decimal('0.7300')
        rationale = 'Domain is stable enough for the next manual-approved progression step.'

        if row['under_observation']:
            action = RoadmapRecommendationAction.REQUIRE_STABILIZATION_FIRST
            reason_codes = ['UNDER_OBSERVATION']
            rationale = 'Domain is still under autonomy rollout observation; stabilize first.'
            blocked_domains.add(slug)
            confidence = Decimal('0.9100')
            evidence_refs.append({'type': 'autonomy_rollout', 'status': row['rollout_status']})

        if row['freeze_warning']:
            action = RoadmapRecommendationAction.FREEZE_DOMAIN
            reason_codes = ['FREEZE_WARNING']
            rationale = 'Autonomy rollout raised a freeze recommendation for this domain.'
            frozen_domains.add(slug)
            blocked_domains.add(slug)
            confidence = Decimal('0.9500')
            evidence_refs.append({'type': 'autonomy_rollout', 'status': row['rollout_status']})

        if row['rollback_warning']:
            action = RoadmapRecommendationAction.ROLLBACK_DOMAIN
            reason_codes = ['ROLLBACK_WARNING']
            rationale = 'Autonomy rollout recommends rollback before any further promotions.'
            frozen_domains.add(slug)
            blocked_domains.add(slug)
            proposed_stage = AutonomyStage.MANUAL
            confidence = Decimal('0.9700')
            evidence_refs.append({'type': 'autonomy_rollout', 'status': row['rollout_status']})

        if row['is_degraded']:
            action = RoadmapRecommendationAction.FREEZE_DOMAIN
            reason_codes = ['DEGRADED_DOMAIN']
            rationale = 'Domain status is degraded/blocked and should be frozen.'
            frozen_domains.add(slug)
            blocked_domains.add(slug)
            confidence = Decimal('0.9800')
            evidence_refs.append({'type': 'autonomy_stage_state', 'status': row['status']})

        profile = profiles.get(slug)
        if profile and profile.criticality == 'CRITICAL' and action == RoadmapRecommendationAction.PROMOTE_DOMAIN:
            confidence = Decimal('0.6600')
            reason_codes.append('CRITICAL_DOMAIN_MANUAL_GATE')
            rationale = 'Critical domain can progress only with conservative manual-first gating.'

        drafts.append(
            RecommendationDraft(
                domain=domains_by_slug[slug],
                action=action,
                current_stage=current_stage,
                proposed_stage=proposed_stage,
                rationale=rationale,
                reason_codes=reason_codes,
                confidence=confidence,
                evidence_refs=evidence_refs,
            )
        )

    for dependency in dependencies:
        source_slug = dependency.source_domain.slug
        target_slug = dependency.target_domain.slug
        source_row = by_slug.get(source_slug)
        target_row = by_slug.get(target_slug)
        if not source_row or not target_row:
            continue

        if dependency.dependency_type == DomainDependencyType.REQUIRES_STABLE:
            if target_row['status'] != 'ACTIVE' or target_row['under_observation']:
                blocked_domains.add(source_slug)
                drafts.append(
                    RecommendationDraft(
                        domain=dependency.source_domain,
                        action=RoadmapRecommendationAction.REQUIRE_STABILIZATION_FIRST,
                        current_stage=source_row['current_stage'],
                        proposed_stage=source_row['current_stage'],
                        rationale=f"{source_slug} requires {target_slug} to be stable first.",
                        reason_codes=['REQUIRES_STABLE', f'TARGET_{target_row["status"]}'],
                        confidence=Decimal('0.9200'),
                        evidence_refs=[{'type': 'dependency', 'dependency_id': dependency.id}, {'type': 'target_domain', 'domain': target_slug}],
                    )
                )

        if dependency.dependency_type == DomainDependencyType.BLOCKS_IF_DEGRADED and target_row['is_degraded']:
            blocked_domains.add(source_slug)
            drafts.append(
                RecommendationDraft(
                    domain=dependency.source_domain,
                    action=RoadmapRecommendationAction.FREEZE_DOMAIN,
                    current_stage=source_row['current_stage'],
                    proposed_stage=source_row['current_stage'],
                    rationale=f"{source_slug} is blocked while {target_slug} remains degraded.",
                    reason_codes=['BLOCKS_IF_DEGRADED'],
                    confidence=Decimal('0.9600'),
                    evidence_refs=[{'type': 'dependency', 'dependency_id': dependency.id}, {'type': 'target_domain', 'domain': target_slug}],
                )
            )
            frozen_domains.add(source_slug)

        if dependency.dependency_type == DomainDependencyType.RECOMMENDED_BEFORE:
            drafts.append(
                RecommendationDraft(
                    domain=dependency.source_domain,
                    action=RoadmapRecommendationAction.SEQUENCE_BEFORE,
                    current_stage=source_row['current_stage'],
                    proposed_stage=source_row['current_stage'],
                    rationale=f"Promote {target_slug} before {source_slug} for safer sequencing.",
                    reason_codes=['RECOMMENDED_BEFORE'],
                    confidence=Decimal('0.7700'),
                    evidence_refs=[{'type': 'dependency', 'dependency_id': dependency.id}],
                )
            )

        if dependency.dependency_type == DomainDependencyType.INCOMPATIBLE_PARALLEL:
            drafts.append(
                RecommendationDraft(
                    domain=dependency.source_domain,
                    action=RoadmapRecommendationAction.DO_NOT_PROMOTE_IN_PARALLEL,
                    current_stage=source_row['current_stage'],
                    proposed_stage=source_row['current_stage'],
                    rationale=f"Avoid promoting {source_slug} in parallel with {target_slug}.",
                    reason_codes=['INCOMPATIBLE_PARALLEL'],
                    confidence=Decimal('0.8900'),
                    evidence_refs=[{'type': 'dependency', 'dependency_id': dependency.id}, {'type': 'paired_domain', 'domain': target_slug}],
                )
            )

    return drafts, {
        'blocked_domains': sorted(blocked_domains),
        'frozen_domains': sorted(frozen_domains),
    }


def persist_recommendations(*, plan, drafts: list[RecommendationDraft]) -> list[RoadmapRecommendation]:
    recommendations: list[RoadmapRecommendation] = []
    for draft in drafts:
        recommendations.append(
            RoadmapRecommendation.objects.create(
                plan=plan,
                domain=draft.domain,
                action=draft.action,
                current_stage=draft.current_stage,
                proposed_stage=draft.proposed_stage,
                rationale=draft.rationale,
                reason_codes=draft.reason_codes,
                confidence=draft.confidence,
                evidence_refs=draft.evidence_refs,
                metadata={},
            )
        )
    return recommendations
