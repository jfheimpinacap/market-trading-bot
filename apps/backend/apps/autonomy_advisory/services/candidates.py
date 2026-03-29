from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_advisory.models import AdvisoryArtifact, AdvisoryArtifactStatus
from apps.autonomy_insights.models import CampaignInsight, RecommendationTarget


@dataclass(frozen=True)
class AdvisoryCandidate:
    insight_id: int
    campaign_id: int | None
    campaign_title: str | None
    insight_type: str
    recommendation_target: str
    recommendation_type: str
    review_status: str
    ready_for_emission: bool
    existing_artifact: int | None
    blockers: list[str]
    metadata: dict


def map_target_to_artifact(recommendation_target: str) -> str | None:
    return {
        RecommendationTarget.MEMORY: 'MEMORY_PRECEDENT_NOTE',
        RecommendationTarget.ROADMAP: 'ROADMAP_GOVERNANCE_NOTE',
        RecommendationTarget.SCENARIO: 'SCENARIO_CAUTION_NOTE',
        RecommendationTarget.PROGRAM: 'PROGRAM_POLICY_NOTE',
        RecommendationTarget.MANAGER: 'MANAGER_REVIEW_NOTE',
        RecommendationTarget.OPERATOR_REVIEW: 'MANAGER_REVIEW_NOTE',
    }.get(recommendation_target)


def build_advisory_candidates() -> list[AdvisoryCandidate]:
    rows: list[AdvisoryCandidate] = []
    insights = CampaignInsight.objects.select_related('campaign').order_by('-created_at', '-id')[:500]

    for insight in insights:
        recommendation_type = map_target_to_artifact(insight.recommendation_target)
        blockers: list[str] = []
        if not insight.reviewed:
            blockers.append('INSIGHT_NOT_REVIEWED')
        if not recommendation_type:
            blockers.append('UNSUPPORTED_TARGET')

        existing = AdvisoryArtifact.objects.filter(insight=insight, artifact_type=recommendation_type or '').order_by('-created_at', '-id').first()
        if existing and existing.artifact_status in {AdvisoryArtifactStatus.EMITTED, AdvisoryArtifactStatus.DUPLICATE_SKIPPED}:
            blockers.append('ALREADY_EMITTED')

        rows.append(
            AdvisoryCandidate(
                insight_id=insight.id,
                campaign_id=insight.campaign_id,
                campaign_title=insight.campaign.title if insight.campaign_id else None,
                insight_type=insight.insight_type,
                recommendation_target=insight.recommendation_target,
                recommendation_type=recommendation_type or 'REQUIRE_MANUAL_ADVISORY_REVIEW',
                review_status='REVIEWED' if insight.reviewed else 'PENDING_REVIEW',
                ready_for_emission=not blockers,
                existing_artifact=existing.id if existing else None,
                blockers=blockers,
                metadata={'insight_confidence': str(insight.confidence), 'insight_metadata': insight.metadata},
            )
        )
    return rows
