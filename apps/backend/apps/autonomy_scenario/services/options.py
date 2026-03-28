from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_manager.models import AutonomyStage
from apps.autonomy_roadmap.models import DomainDependencyType


@dataclass
class ScenarioOptionDraft:
    option_key: str
    option_type: str
    domains: list[str]
    order: list[str]
    requested_stages: dict[str, str]
    is_bundle: bool
    notes: str
    metadata: dict


def _next_stage(current_stage: str) -> str:
    if current_stage == AutonomyStage.MANUAL:
        return AutonomyStage.ASSISTED
    if current_stage == AutonomyStage.ASSISTED:
        return AutonomyStage.SUPERVISED_AUTOPILOT
    return current_stage


def build_scenario_option_drafts(*, evidence: dict, dependencies: list) -> list[ScenarioOptionDraft]:
    rows_by_slug = {row['domain_slug']: row for row in evidence.get('domains', [])}
    promote_candidates = [slug for slug, row in rows_by_slug.items() if not row['is_degraded'] and not row['freeze_warning'] and not row['rollback_warning']]
    blocked = {slug for slug, row in rows_by_slug.items() if row['under_observation'] or row['freeze_warning'] or row['rollback_warning'] or row['is_degraded']}
    drafts: list[ScenarioOptionDraft] = []

    for slug in promote_candidates[:6]:
        row = rows_by_slug[slug]
        drafts.append(
            ScenarioOptionDraft(
                option_key=f'single:{slug}',
                option_type='PROMOTE_SINGLE_DOMAIN',
                domains=[slug],
                order=[slug],
                requested_stages={slug: _next_stage(row['current_stage'])},
                is_bundle=False,
                notes='Promote one domain with a conservative manual gate.',
                metadata={'source': 'autonomy_roadmap_candidate'},
            )
        )

    for dependency in dependencies:
        source = dependency.source_domain.slug
        target = dependency.target_domain.slug
        if source not in rows_by_slug or target not in rows_by_slug:
            continue

        if dependency.dependency_type == DomainDependencyType.RECOMMENDED_BEFORE:
            drafts.append(
                ScenarioOptionDraft(
                    option_key=f'sequence:{target}:{source}',
                    option_type='SEQUENCE_TWO_DOMAINS',
                    domains=[target, source],
                    order=[target, source],
                    requested_stages={
                        target: _next_stage(rows_by_slug[target]['current_stage']),
                        source: _next_stage(rows_by_slug[source]['current_stage']),
                    },
                    is_bundle=False,
                    notes=f'Sequence {target} before {source} based on explicit roadmap dependency.',
                    metadata={'dependency_id': dependency.id, 'dependency_type': dependency.dependency_type},
                )
            )

        if dependency.dependency_type == DomainDependencyType.INCOMPATIBLE_PARALLEL:
            drafts.append(
                ScenarioOptionDraft(
                    option_key=f'bundle:{source}:{target}',
                    option_type='BUNDLE_DOMAINS',
                    domains=[source, target],
                    order=[source, target],
                    requested_stages={
                        source: _next_stage(rows_by_slug[source]['current_stage']),
                        target: _next_stage(rows_by_slug[target]['current_stage']),
                    },
                    is_bundle=True,
                    notes='Parallel bundle candidate to evaluate conflict risk before any manual apply.',
                    metadata={'dependency_id': dependency.id, 'dependency_type': dependency.dependency_type},
                )
            )

    for slug in sorted(blocked)[:4]:
        promotion_target = next((candidate for candidate in promote_candidates if candidate != slug), None)
        if not promotion_target:
            continue
        drafts.append(
            ScenarioOptionDraft(
                option_key=f'freeze:{slug}:promote:{promotion_target}',
                option_type='FREEZE_AND_PROMOTE_OTHER',
                domains=[slug, promotion_target],
                order=[slug, promotion_target],
                requested_stages={promotion_target: _next_stage(rows_by_slug[promotion_target]['current_stage'])},
                is_bundle=False,
                notes=f'Keep {slug} frozen while promoting a cleaner domain trajectory.',
                metadata={'frozen_domain': slug},
            )
        )
        drafts.append(
            ScenarioOptionDraft(
                option_key=f'delay:{slug}',
                option_type='DELAY_UNTIL_STABLE',
                domains=[slug],
                order=[slug],
                requested_stages={},
                is_bundle=False,
                notes='Delay promotion until rollout/incident posture is stable.',
                metadata={'blocked_domain': slug},
            )
        )

    deduped: dict[str, ScenarioOptionDraft] = {draft.option_key: draft for draft in drafts}
    return list(deduped.values())
