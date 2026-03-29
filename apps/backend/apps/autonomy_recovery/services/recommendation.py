from __future__ import annotations

from apps.autonomy_recovery.models import RecoveryRecommendation
from apps.autonomy_recovery.services.candidates import RecoveryCandidateContext


def create_recommendation(*, run, context: RecoveryCandidateContext, snapshot, actor: str) -> RecoveryRecommendation:
    status = snapshot.recovery_status
    recommendation_type = 'REQUIRE_MORE_RECOVERY'
    reason_codes = ['recovery_assessment']

    if status == 'READY_TO_RESUME':
        recommendation_type = 'RESUME_CAMPAIGN'
        reason_codes = ['blockers_cleared', 'safe_resume_ready']
    elif status == 'KEEP_PAUSED':
        recommendation_type = 'KEEP_PAUSED'
        reason_codes = ['pending_recovery_blockers']
    elif status == 'BLOCKED':
        recommendation_type = 'REQUIRE_MORE_RECOVERY'
        reason_codes = ['global_or_domain_block']
    elif status == 'REVIEW_ABORT':
        recommendation_type = 'REVIEW_FOR_ABORT'
        reason_codes = ['sustained_pressure']
    elif status == 'CLOSE_CANDIDATE':
        recommendation_type = 'CLOSE_CAMPAIGN'
        reason_codes = ['aged_paused_campaign', 'high_recovery_risk']

    if context.pending_approvals_count > 0 and recommendation_type in {'REVIEW_FOR_ABORT', 'CLOSE_CAMPAIGN', 'RESUME_CAMPAIGN'}:
        recommendation_type = 'ESCALATE_TO_APPROVAL'
        reason_codes.append('approval_required')

    return RecoveryRecommendation.objects.create(
        recovery_run=run,
        recommendation_type=recommendation_type,
        target_campaign=context.campaign,
        rationale=snapshot.rationale,
        reason_codes=reason_codes,
        confidence=max(0.1, min(0.99, snapshot.recovery_score / 100)),
        blockers=snapshot.metadata.get('blockers', []),
        impacted_domains=(context.campaign.metadata or {}).get('domains', []),
        metadata={'actor': actor, 'resume_readiness': snapshot.resume_readiness},
    )
