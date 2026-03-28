from __future__ import annotations

from django.db import transaction

from apps.autonomy_campaign.models import AutonomyCampaign, AutonomyCampaignSourceType, AutonomyCampaignStatus
from apps.autonomy_campaign.services.steps import (
    build_step_drafts_from_roadmap,
    build_step_drafts_from_scenario,
    persist_steps,
)
from apps.autonomy_roadmap.models import AutonomyRoadmapPlan
from apps.autonomy_scenario.models import AutonomyScenarioRun


@transaction.atomic
def create_campaign(*, source_type: str, source_object_id: str, title: str, summary: str, metadata: dict | None = None) -> AutonomyCampaign:
    campaign = AutonomyCampaign.objects.create(
        source_type=source_type,
        source_object_id=source_object_id,
        title=title,
        summary=summary,
        status=AutonomyCampaignStatus.DRAFT,
        metadata=metadata or {},
    )

    if source_type == AutonomyCampaignSourceType.ROADMAP_PLAN:
        plan = AutonomyRoadmapPlan.objects.prefetch_related('recommendations__domain').get(pk=int(source_object_id))
        drafts = build_step_drafts_from_roadmap(plan)
    elif source_type == AutonomyCampaignSourceType.SCENARIO_RUN:
        run = AutonomyScenarioRun.objects.prefetch_related('options').get(pk=int(source_object_id))
        drafts = build_step_drafts_from_scenario(run=run)
    else:
        drafts = []

    steps = persist_steps(campaign=campaign, drafts=drafts)
    campaign.total_steps = len(steps)
    campaign.status = AutonomyCampaignStatus.READY if steps else AutonomyCampaignStatus.DRAFT
    campaign.current_wave = min((step.wave for step in steps), default=1)
    campaign.metadata = {
        **(campaign.metadata or {}),
        'manual_first': True,
        'sandbox_only': True,
        'recommendation_first': True,
    }
    campaign.save(update_fields=['total_steps', 'status', 'current_wave', 'metadata', 'updated_at'])
    return campaign
