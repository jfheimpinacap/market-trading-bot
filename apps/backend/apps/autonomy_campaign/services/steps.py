from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignActionType, AutonomyCampaignStep
from apps.autonomy_manager.models import AutonomyDomain
from apps.autonomy_roadmap.models import AutonomyRoadmapPlan, DomainDependency, DomainDependencyType
from apps.autonomy_scenario.models import AutonomyScenarioRun, ScenarioOption


@dataclass
class StepDraft:
    wave: int
    domain: AutonomyDomain
    action_type: str
    rationale: str
    metadata: dict


def _build_step_set(*, wave: int, domain: AutonomyDomain, requested_stage: str, rationale: str, source_metadata: dict | None = None) -> list[StepDraft]:
    return [
        StepDraft(wave=wave, domain=domain, action_type=AutonomyCampaignActionType.APPLY_TRANSITION, rationale=rationale, metadata={'requested_stage': requested_stage, **(source_metadata or {})}),
        StepDraft(wave=wave, domain=domain, action_type=AutonomyCampaignActionType.START_ROLLOUT, rationale='Open rollout monitor after manual transition apply.', metadata={'requested_stage': requested_stage}),
        StepDraft(wave=wave, domain=domain, action_type=AutonomyCampaignActionType.EVALUATE_ROLLOUT, rationale='Wait for rollout observation/evaluation before next wave.', metadata={'requested_stage': requested_stage}),
    ]


def build_step_drafts_from_roadmap(plan: AutonomyRoadmapPlan) -> list[StepDraft]:
    sequence = list(plan.recommended_sequence or [])
    if not sequence:
        return []

    dependencies = DomainDependency.objects.select_related('source_domain', 'target_domain').all()
    dependency_lookup: dict[str, set[str]] = {}
    for row in dependencies:
        if row.dependency_type in {DomainDependencyType.RECOMMENDED_BEFORE, DomainDependencyType.REQUIRES_STABLE}:
            dependency_lookup.setdefault(row.source_domain.slug, set()).add(row.target_domain.slug)

    recommendations = {item.domain.slug: item for item in plan.recommendations.select_related('domain').all()}
    blocked = set(plan.blocked_domains or [])
    waves: dict[str, int] = {}
    for slug in sequence:
        base_wave = 1
        for dep in dependency_lookup.get(slug, set()):
            if dep in waves:
                base_wave = max(base_wave, waves[dep] + 1)
        waves[slug] = base_wave

    drafts: list[StepDraft] = []
    for slug in sequence:
        rec = recommendations.get(slug)
        if not rec or slug in blocked or not rec.proposed_stage:
            continue
        drafts.extend(_build_step_set(wave=waves.get(slug, 1), domain=rec.domain, requested_stage=rec.proposed_stage, rationale=rec.rationale, source_metadata={'roadmap_recommendation_id': rec.id}))
    return drafts


def build_step_drafts_from_scenario(*, run: AutonomyScenarioRun, option: ScenarioOption | None = None) -> list[StepDraft]:
    selected_option = option or run.options.filter(option_key=run.selected_option_key).first() or run.options.first()
    if not selected_option:
        return []
    order = list(selected_option.order or selected_option.domains or [])
    requested_stages = dict(selected_option.requested_stages or {})
    drafts: list[StepDraft] = []
    for idx, slug in enumerate(order):
        domain = AutonomyDomain.objects.filter(slug=slug).first()
        stage = requested_stages.get(slug)
        if not domain or not stage:
            continue
        drafts.extend(_build_step_set(wave=idx + 1, domain=domain, requested_stage=stage, rationale=f'Scenario option {selected_option.option_key}: staged manual-first transition for {slug}.', source_metadata={'scenario_option_id': selected_option.id, 'scenario_option_key': selected_option.option_key}))
    return drafts


def persist_steps(*, campaign: AutonomyCampaign, drafts: list[StepDraft]) -> list[AutonomyCampaignStep]:
    steps: list[AutonomyCampaignStep] = []
    order = 1
    action_rank = {
        AutonomyCampaignActionType.APPLY_TRANSITION: 1,
        AutonomyCampaignActionType.START_ROLLOUT: 2,
        AutonomyCampaignActionType.EVALUATE_ROLLOUT: 3,
    }
    for draft in sorted(drafts, key=lambda row: (row.wave, row.domain.slug, action_rank.get(row.action_type, 99))):
        step = AutonomyCampaignStep.objects.create(
            campaign=campaign,
            step_order=order,
            wave=draft.wave,
            domain=draft.domain,
            action_type=draft.action_type,
            rationale=draft.rationale,
            metadata=draft.metadata,
        )
        steps.append(step)
        order += 1
    return steps
