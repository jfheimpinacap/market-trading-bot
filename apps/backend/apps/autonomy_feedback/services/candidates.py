from __future__ import annotations

from dataclasses import dataclass

from apps.autonomy_followup.models import CampaignFollowup, FollowupStatus

from .status import evaluate_downstream


@dataclass(slots=True)
class FeedbackCandidate:
    campaign_id: int
    campaign_title: str
    followup_id: int
    followup_type: str
    followup_status: str
    linked_artifact: str | None
    downstream_status: str
    ready_for_resolution: bool
    blockers: list[str]
    metadata: dict


def build_feedback_candidates() -> list[FeedbackCandidate]:
    rows = (
        CampaignFollowup.objects.select_related('campaign', 'linked_memory_document', 'linked_postmortem_request')
        .filter(followup_status=FollowupStatus.EMITTED)
        .order_by('-updated_at', '-id')
    )

    candidates: list[FeedbackCandidate] = []
    for followup in rows:
        evaluation = evaluate_downstream(followup)
        artifact = None
        if followup.linked_memory_document_id:
            artifact = f'memory:{followup.linked_memory_document_id}'
        elif followup.linked_postmortem_request_id:
            artifact = f'postmortem_request:{followup.linked_postmortem_request_id}'
        elif followup.linked_feedback_artifact:
            artifact = followup.linked_feedback_artifact

        candidates.append(
            FeedbackCandidate(
                campaign_id=followup.campaign_id,
                campaign_title=followup.campaign.title,
                followup_id=followup.id,
                followup_type=followup.followup_type,
                followup_status=followup.followup_status,
                linked_artifact=artifact,
                downstream_status=evaluation.downstream_status,
                ready_for_resolution=evaluation.resolution_status in {'COMPLETED', 'REJECTED'},
                blockers=evaluation.blockers,
                metadata={'reason_codes': evaluation.reason_codes},
            )
        )

    return candidates
