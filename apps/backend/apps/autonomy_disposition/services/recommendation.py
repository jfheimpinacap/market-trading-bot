from __future__ import annotations

from apps.autonomy_disposition.models import CampaignDispositionType, DispositionRecommendation, DispositionRecommendationType


def build_disposition_recommendation_payload(*, context, readiness):
    mapping = {
        'READY_TO_CLOSE': (DispositionRecommendationType.CLOSE_CAMPAIGN, CampaignDispositionType.CLOSED, 0.84),
        'READY_TO_ABORT': (DispositionRecommendationType.ABORT_CAMPAIGN, CampaignDispositionType.ABORTED, 0.9),
        'READY_TO_RETIRE': (DispositionRecommendationType.RETIRE_CAMPAIGN, CampaignDispositionType.RETIRED, 0.78),
        'REQUIRE_MORE_REVIEW': (DispositionRecommendationType.KEEP_CAMPAIGN_OPEN, CampaignDispositionType.KEPT_OPEN, 0.66),
        'KEEP_OPEN': (DispositionRecommendationType.KEEP_CAMPAIGN_OPEN, CampaignDispositionType.KEPT_OPEN, 0.7),
    }
    rec_type, disposition_type, confidence = mapping[readiness['disposition_readiness']]

    if context.campaign.status == 'COMPLETED' and readiness['disposition_readiness'] == 'READY_TO_CLOSE':
        rec_type = DispositionRecommendationType.RECORD_COMPLETION
        disposition_type = CampaignDispositionType.COMPLETED_RECORDED
        confidence = 0.88

    requires_approval = disposition_type in {CampaignDispositionType.ABORTED, CampaignDispositionType.RETIRED} or bool(readiness['blockers'])
    if requires_approval:
        readiness['reason_codes'].append('approval_required_for_sensitive_disposition')

    return {
        'recommendation_type': rec_type,
        'disposition_type': disposition_type,
        'requires_approval': requires_approval,
        'confidence': confidence,
        'rationale': readiness['rationale'],
        'reason_codes': readiness['reason_codes'],
        'blockers': readiness['blockers'],
    }


def create_recommendation(*, run, context, recommendation, actor: str):
    return DispositionRecommendation.objects.create(
        disposition_run=run,
        recommendation_type=recommendation['recommendation_type'],
        target_campaign=context.campaign,
        rationale=recommendation['rationale'],
        reason_codes=recommendation['reason_codes'],
        confidence=recommendation['confidence'],
        blockers=recommendation['blockers'],
        impacted_domains=context.campaign.metadata.get('domains', []),
        metadata={'actor': actor, 'suggested_disposition_type': recommendation['disposition_type']},
    )
