from __future__ import annotations

from decimal import Decimal

from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_program.models import ProgramRecommendation, ProgramRecommendationType
from apps.autonomy_program.services.rules import evaluate_concurrency_conflicts, get_active_campaigns_queryset
from apps.autonomy_program.services.state import recompute_program_state


def generate_program_recommendations(*, snapshots: list) -> list[ProgramRecommendation]:
    state = recompute_program_state()
    active_campaigns = list(get_active_campaigns_queryset())
    conflict_eval = evaluate_concurrency_conflicts(active_campaigns=active_campaigns)
    recommendations: list[ProgramRecommendation] = []

    if state.concurrency_posture == 'FROZEN':
        recommendations.append(
            ProgramRecommendation.objects.create(
                recommendation_type=ProgramRecommendationType.HOLD_NEW_CAMPAIGNS,
                rationale='Critical incidents are active. Freeze new autonomy campaign starts until stabilized.',
                reason_codes=['CRITICAL_INCIDENT_ACTIVE'],
                confidence=Decimal('0.9500'),
                impacted_domains=state.metadata.get('degraded_domains', []),
                blockers=['critical_incident'],
            )
        )

    if state.concurrency_posture in ['CONSTRAINED', 'HIGH_RISK'] and state.degraded_domains_count > 0:
        recommendations.append(
            ProgramRecommendation.objects.create(
                recommendation_type=ProgramRecommendationType.HOLD_NEW_CAMPAIGNS,
                rationale='Program is degraded; hold new campaigns and stabilize affected domains first.',
                reason_codes=['DEGRADED_POSTURE_ACTIVE'],
                confidence=Decimal('0.8200'),
                impacted_domains=state.metadata.get('degraded_domains', []),
                blockers=['degraded_posture'],
            )
        )

    for conflict in conflict_eval['conflicts']:
        if conflict['reason_code'] == 'MAX_ACTIVE_EXCEEDED':
            recommendations.append(
                ProgramRecommendation.objects.create(
                    recommendation_type=ProgramRecommendationType.REORDER_QUEUE,
                    rationale='Active campaign capacity exceeded; reorder queue and keep only highest-priority campaigns running.',
                    reason_codes=['MAX_ACTIVE_EXCEEDED'],
                    confidence=Decimal('0.8300'),
                    impacted_domains=state.locked_domains,
                    blockers=['capacity_limit'],
                    metadata=conflict,
                )
            )
        if conflict['reason_code'] == 'INCOMPATIBLE_DOMAINS_ACTIVE':
            for campaign_id in conflict['details']['campaign_ids']:
                target = AutonomyCampaign.objects.filter(pk=campaign_id).first()
                if not target:
                    continue
                recommendations.append(
                    ProgramRecommendation.objects.create(
                        recommendation_type=ProgramRecommendationType.PAUSE_CAMPAIGN,
                        target_campaign=target,
                        rationale='Campaign touches domains that currently conflict with another active campaign.',
                        reason_codes=['INCOMPATIBLE_DOMAINS_ACTIVE'],
                        confidence=Decimal('0.7900'),
                        impacted_domains=conflict['details']['pair'],
                        blockers=['domain_conflict'],
                        metadata=conflict,
                    )
                )

    at_risk = [snapshot for snapshot in snapshots if snapshot.health_status in ['BLOCKED', 'AT_RISK']]
    for snapshot in at_risk:
        recommendations.append(
            ProgramRecommendation.objects.create(
                recommendation_type=ProgramRecommendationType.WAIT_FOR_STABILIZATION,
                target_campaign=snapshot.campaign,
                rationale='Campaign health is degraded; wait for approvals, incident recovery, or rollout stabilization before resuming.',
                reason_codes=[snapshot.health_status, 'HEALTH_GOVERNANCE'],
                confidence=Decimal('0.7600'),
                impacted_domains=snapshot.metadata.get('domains', []),
                blockers=['health_not_green'],
            )
        )

    if not recommendations:
        recommendations.append(
            ProgramRecommendation.objects.create(
                recommendation_type=ProgramRecommendationType.SAFE_TO_START_NEXT,
                rationale='No major conflicts detected and posture is stable for the next campaign.',
                reason_codes=['NO_BLOCKERS_DETECTED'],
                confidence=Decimal('0.7000'),
                impacted_domains=state.locked_domains,
                blockers=[],
            )
        )

    return recommendations
