from __future__ import annotations

from dataclasses import dataclass

from apps.mission_control.models import (
    GovernanceAutoResolutionDecision,
    GovernanceAutoResolutionDecisionStatus,
    GovernanceAutoResolutionDecisionType,
    GovernanceAutoResolutionEffectType,
    GovernanceAutoResolutionRecord,
    GovernanceAutoResolutionRecordStatus,
    GovernanceReviewResolutionType,
)
from apps.mission_control.services.resolve import resolve_governance_review_item


@dataclass
class AutoResolveResult:
    status: str
    effect_type: str
    summary: str
    metadata: dict


def apply_auto_resolution_decision(*, decision: GovernanceAutoResolutionDecision) -> GovernanceAutoResolutionRecord:
    item = decision.linked_review_item

    if not decision.auto_applicable:
        decision.decision_status = GovernanceAutoResolutionDecisionStatus.SKIPPED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return GovernanceAutoResolutionRecord.objects.create(
            linked_review_item=item,
            linked_auto_resolution_decision=decision,
            record_status=GovernanceAutoResolutionRecordStatus.SKIPPED,
            effect_type=GovernanceAutoResolutionEffectType.NO_CHANGE,
            record_summary='Auto-resolution decision was not auto-applicable.',
            metadata={'decision_type': decision.decision_type},
        )

    if decision.decision_type == GovernanceAutoResolutionDecisionType.DO_NOT_AUTO_RESOLVE:
        decision.decision_status = GovernanceAutoResolutionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return GovernanceAutoResolutionRecord.objects.create(
            linked_review_item=item,
            linked_auto_resolution_decision=decision,
            record_status=GovernanceAutoResolutionRecordStatus.BLOCKED,
            effect_type=GovernanceAutoResolutionEffectType.NO_CHANGE,
            record_summary='Item requires manual governance resolution.',
            metadata={'decision_type': decision.decision_type},
        )

    resolution_type = GovernanceReviewResolutionType.REQUIRE_FOLLOWUP
    effect_type = GovernanceAutoResolutionEffectType.FOLLOWUP_MARKED

    if decision.decision_type == GovernanceAutoResolutionDecisionType.AUTO_DISMISS:
        resolution_type = GovernanceReviewResolutionType.DISMISS_AS_EXPECTED
        effect_type = GovernanceAutoResolutionEffectType.DISMISSED
    elif decision.decision_type == GovernanceAutoResolutionDecisionType.AUTO_RETRY_SAFE_APPLY:
        resolution_type = GovernanceReviewResolutionType.RETRY_SAFE_APPLY
        effect_type = GovernanceAutoResolutionEffectType.RETRY_SAFE_APPLY_TRIGGERED

    try:
        resolution = resolve_governance_review_item(
            item=item,
            resolution_type=resolution_type,
            resolution_summary=f'Auto-resolution applied from decision {decision.id}.',
            metadata={
                'auto_resolution_decision_id': decision.id,
                'reason_codes': decision.reason_codes,
                **(decision.metadata or {}),
            },
        )
    except Exception as exc:
        decision.decision_status = GovernanceAutoResolutionDecisionStatus.BLOCKED
        decision.save(update_fields=['decision_status', 'updated_at'])
        return GovernanceAutoResolutionRecord.objects.create(
            linked_review_item=item,
            linked_auto_resolution_decision=decision,
            record_status=GovernanceAutoResolutionRecordStatus.FAILED,
            effect_type=GovernanceAutoResolutionEffectType.NO_CHANGE,
            record_summary='Auto-resolution apply failed; item left for manual review.',
            metadata={'error': str(exc)},
        )

    decision_status = GovernanceAutoResolutionDecisionStatus.APPLIED
    record_status = GovernanceAutoResolutionRecordStatus.APPLIED
    if resolution.resolution_status == 'BLOCKED':
        decision_status = GovernanceAutoResolutionDecisionStatus.BLOCKED
        record_status = GovernanceAutoResolutionRecordStatus.BLOCKED

    decision.decision_status = decision_status
    decision.save(update_fields=['decision_status', 'updated_at'])

    return GovernanceAutoResolutionRecord.objects.create(
        linked_review_item=item,
        linked_auto_resolution_decision=decision,
        record_status=record_status,
        effect_type=effect_type,
        record_summary=resolution.resolution_summary,
        metadata={
            'resolution_id': resolution.id,
            'resolution_type': resolution.resolution_type,
            'resolution_status': resolution.resolution_status,
        },
    )
