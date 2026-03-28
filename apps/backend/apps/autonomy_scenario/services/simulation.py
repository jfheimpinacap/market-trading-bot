from __future__ import annotations

from dataclasses import asdict

from apps.approval_center.services.summary import get_approval_queue_summary
from apps.autonomy_roadmap.models import DomainDependency
from apps.autonomy_roadmap.services.evidence import collect_global_evidence
from apps.autonomy_roadmap.services.plans import list_recommendations_queryset as list_roadmap_recommendations_queryset
from apps.autonomy_scenario.models import AutonomyScenarioRun, ScenarioOption, ScenarioRecommendation, ScenarioRiskEstimate
from apps.autonomy_scenario.services.options import build_scenario_option_drafts
from apps.autonomy_scenario.services.recommendation import build_recommendation_for_option
from apps.autonomy_scenario.services.risk import estimate_option_risk
from apps.incident_commander.services.policies import summarize_incidents


def collect_scenario_evidence() -> dict:
    evidence = collect_global_evidence()
    evidence['roadmap_recommendations'] = [
        {
            'domain_slug': rec.domain.slug,
            'action': rec.action,
            'confidence': str(rec.confidence),
            'reason_codes': rec.reason_codes,
        }
        for rec in list_roadmap_recommendations_queryset()[:100]
    ]
    evidence['approval'] = get_approval_queue_summary()
    evidence['incidents'] = summarize_incidents()
    return evidence


def get_options_preview() -> list[dict]:
    dependencies = list(DomainDependency.objects.select_related('source_domain', 'target_domain').all())
    evidence = collect_scenario_evidence()
    drafts = build_scenario_option_drafts(evidence=evidence, dependencies=dependencies)
    return [asdict(draft) for draft in drafts]


def run_simulation(*, requested_by: str = 'operator-ui', notes: str = '') -> AutonomyScenarioRun:
    dependencies = list(DomainDependency.objects.select_related('source_domain', 'target_domain').all())
    evidence = collect_scenario_evidence()
    option_drafts = build_scenario_option_drafts(evidence=evidence, dependencies=dependencies)

    run = AutonomyScenarioRun.objects.create(
        summary='Autonomy scenario simulation run comparing sequence/bundle what-if options.',
        evidence_snapshot=evidence,
        metadata={'requested_by': requested_by, 'notes': notes, 'manual_first': True, 'simulation_only': True},
    )

    option_rows: list[tuple[ScenarioOption, ScenarioRiskEstimate, ScenarioRecommendation]] = []
    for draft in option_drafts:
        option = ScenarioOption.objects.create(
            run=run,
            option_key=draft.option_key,
            option_type=draft.option_type,
            domains=draft.domains,
            order=draft.order,
            requested_stages=draft.requested_stages,
            is_bundle=draft.is_bundle,
            notes=draft.notes,
            metadata=draft.metadata,
        )
        risk_draft = estimate_option_risk(option=option, evidence=evidence, dependencies=dependencies)
        risk = ScenarioRiskEstimate.objects.create(run=run, option=option, **asdict(risk_draft))

        recommendation_draft = build_recommendation_for_option(option=option, risk=risk)
        recommendation = ScenarioRecommendation.objects.create(
            run=run,
            option=option,
            **asdict(recommendation_draft),
            metadata={'manual_first': True, 'recommendation_only': True},
        )
        option_rows.append((option, risk, recommendation))

    selected = max(option_rows, key=lambda row: row[2].score, default=None)
    if selected:
        run.selected_option_key = selected[0].option_key
        run.selected_recommendation_code = selected[2].recommendation_code
        run.summary = f"{len(option_rows)} options compared; best option={selected[0].option_key} ({selected[2].recommendation_code})."
        run.save(update_fields=['selected_option_key', 'selected_recommendation_code', 'summary', 'updated_at'])
    return run
