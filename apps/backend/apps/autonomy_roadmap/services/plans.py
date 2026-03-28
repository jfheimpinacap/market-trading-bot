from __future__ import annotations

from django.db.models import Count

from apps.autonomy_roadmap.models import AutonomyRoadmapPlan, RoadmapRecommendation, RoadmapRecommendationAction
from apps.autonomy_roadmap.services.bundles import build_bundle_payloads, persist_bundles
from apps.autonomy_roadmap.services.dependencies import list_dependencies
from apps.autonomy_roadmap.services.evidence import collect_global_evidence
from apps.autonomy_roadmap.services.recommendation import build_recommendation_drafts, persist_recommendations


def run_roadmap_plan(*, requested_by: str = 'operator') -> AutonomyRoadmapPlan:
    dependencies = list_dependencies()
    evidence = collect_global_evidence()
    drafts, posture = build_recommendation_drafts(evidence=evidence, dependencies=dependencies)

    promote_domains = sorted({draft.domain.slug for draft in drafts if draft.action == RoadmapRecommendationAction.PROMOTE_DOMAIN})
    recommended_sequence = [slug for slug in promote_domains if slug not in posture['blocked_domains'] and slug not in posture['frozen_domains']]
    summary = f"{len(recommended_sequence)} next moves, {len(posture['blocked_domains'])} blocked, {len(posture['frozen_domains'])} frozen domains."

    plan = AutonomyRoadmapPlan.objects.create(
        summary=summary,
        current_domain_posture=evidence,
        candidate_transitions=[{'domain': slug, 'action': 'PROMOTE_DOMAIN'} for slug in promote_domains],
        blocked_domains=posture['blocked_domains'],
        frozen_domains=posture['frozen_domains'],
        recommended_sequence=recommended_sequence,
        metadata={'requested_by': requested_by},
    )

    persist_recommendations(plan=plan, drafts=drafts)
    bundle_payloads = build_bundle_payloads(dependencies=dependencies, blocked_domains=posture['blocked_domains'])
    persist_bundles(plan=plan, bundle_payloads=bundle_payloads)
    return plan


def build_summary_payload() -> dict:
    latest = AutonomyRoadmapPlan.objects.order_by('-created_at', '-id').first()
    breakdown_rows = (
        RoadmapRecommendation.objects.values('action')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    return {
        'total_plans': AutonomyRoadmapPlan.objects.count(),
        'latest_plan_id': latest.id if latest else None,
        'latest_summary': latest.summary if latest else None,
        'latest_blocked_domains': latest.blocked_domains if latest else [],
        'latest_frozen_domains': latest.frozen_domains if latest else [],
        'latest_recommended_sequence': latest.recommended_sequence if latest else [],
        'recommendation_breakdown': {row['action']: row['total'] for row in breakdown_rows},
    }


def list_plan_queryset():
    return AutonomyRoadmapPlan.objects.prefetch_related('recommendations', 'bundles').order_by('-created_at', '-id')


def list_recommendations_queryset():
    return RoadmapRecommendation.objects.select_related('domain', 'plan').order_by('-created_at', '-id')
