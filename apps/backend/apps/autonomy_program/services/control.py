from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.approval_center.models import ApprovalPriority, ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.autonomy_campaign.models import AutonomyCampaignStatus
from apps.autonomy_program.models import ProgramRecommendation
from apps.autonomy_program.services.health import build_campaign_health_snapshots
from apps.autonomy_program.services.recommendation import generate_program_recommendations
from apps.autonomy_program.services.state import build_program_state_payload


@transaction.atomic
def _apply_pause_gating(recommendations: list[ProgramRecommendation], actor: str) -> int:
    updated = 0
    for recommendation in recommendations:
        if recommendation.recommendation_type != 'PAUSE_CAMPAIGN' or not recommendation.target_campaign:
            continue
        campaign = recommendation.target_campaign
        if campaign.status in [AutonomyCampaignStatus.COMPLETED, AutonomyCampaignStatus.ABORTED, AutonomyCampaignStatus.FAILED]:
            continue
        campaign.status = AutonomyCampaignStatus.BLOCKED
        campaign.metadata = {
            **(campaign.metadata or {}),
            'program_pause_gate': {
                'reason_codes': recommendation.reason_codes,
                'actor': actor,
                'recommendation_id': recommendation.id,
                'gated_at': timezone.now().isoformat(),
            },
        }
        campaign.save(update_fields=['status', 'metadata', 'updated_at'])
        ApprovalRequest.objects.update_or_create(
            source_type=ApprovalSourceType.OTHER,
            source_object_id=f'autonomy_program:pause_campaign:{campaign.id}',
            defaults={
                'title': f'Program pause gate for campaign #{campaign.id}',
                'summary': recommendation.rationale,
                'priority': ApprovalPriority.HIGH,
                'status': ApprovalRequestStatus.PENDING,
                'requested_at': timezone.now(),
                'expires_at': None,
                'metadata': {
                    'source': 'autonomy_program',
                    'campaign_id': campaign.id,
                    'recommendation_id': recommendation.id,
                    'reason_codes': recommendation.reason_codes,
                },
            },
        )
        updated += 1
    return updated


def run_program_review(*, actor: str = 'operator-ui', apply_pause_gating: bool = True) -> dict:
    snapshots = build_campaign_health_snapshots()
    recommendations = generate_program_recommendations(snapshots=snapshots)
    paused = _apply_pause_gating(recommendations, actor) if apply_pause_gating else 0
    state_payload = build_program_state_payload()
    return {
        'state': state_payload['state'],
        'health_snapshots': snapshots,
        'recommendations': recommendations,
        'pause_gates_applied': paused,
        'conflicts': state_payload['conflicts'],
    }
