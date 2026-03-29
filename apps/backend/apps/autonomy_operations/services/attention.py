from __future__ import annotations

from decimal import Decimal

from apps.autonomy_operations.models import (
    CampaignAttentionSeverity,
    CampaignAttentionSignal,
    CampaignAttentionSignalStatus,
    CampaignAttentionSignalType,
    CampaignRuntimeSnapshot,
)


def _upsert_signal(*, snapshot: CampaignRuntimeSnapshot, signal_type: str, severity: str, rationale: str, reason_codes: list[str], blockers: list[str]) -> CampaignAttentionSignal:
    return CampaignAttentionSignal.objects.create(
        campaign=snapshot.campaign,
        severity=severity,
        signal_type=signal_type,
        status=CampaignAttentionSignalStatus.OPEN,
        rationale=rationale,
        reason_codes=reason_codes,
        blockers=blockers,
        linked_trace=f'autonomy_campaign:{snapshot.campaign_id}',
        metadata={'runtime_snapshot_id': snapshot.id},
    )


def generate_attention_signals(snapshot: CampaignRuntimeSnapshot) -> list[CampaignAttentionSignal]:
    signals: list[CampaignAttentionSignal] = []

    if snapshot.runtime_status == 'STALLED':
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.STALLED_PROGRESS,
                severity=CampaignAttentionSeverity.HIGH,
                rationale='Campaign progress has stalled beyond conservative threshold.',
                reason_codes=['STALLED_PROGRESS'],
                blockers=snapshot.blockers,
            )
        )

    if snapshot.pending_approvals_count > 0:
        severity = CampaignAttentionSeverity.HIGH if (snapshot.stalled_duration_seconds or 0) > 1800 else CampaignAttentionSeverity.MEDIUM
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.APPROVAL_DELAY,
                severity=severity,
                rationale='Campaign is waiting for pending approval/checkpoint decisions.',
                reason_codes=['WAITING_APPROVAL'],
                blockers=snapshot.blockers,
            )
        )

    if snapshot.blocked_steps_count > 0 or snapshot.runtime_status == 'BLOCKED':
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.BLOCKED_CHECKPOINT,
                severity=CampaignAttentionSeverity.HIGH,
                rationale='Campaign has blocked runtime steps and cannot continue without intervention.',
                reason_codes=['BLOCKED_RUNTIME'],
                blockers=snapshot.blockers,
            )
        )

    if snapshot.incident_impact > 0:
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.INCIDENT_IMPACT,
                severity=CampaignAttentionSeverity.CRITICAL if snapshot.incident_impact > 1 else CampaignAttentionSeverity.HIGH,
                rationale='Active incidents are impacting this campaign runtime envelope.',
                reason_codes=['INCIDENT_IMPACT'],
                blockers=snapshot.blockers,
            )
        )

    if snapshot.degraded_impact > 0:
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.DEGRADED_PRESSURE,
                severity=CampaignAttentionSeverity.MEDIUM,
                rationale='Global degraded mode introduces pressure for campaign runtime progression.',
                reason_codes=['DEGRADED_MODE'],
                blockers=snapshot.blockers,
            )
        )

    if snapshot.rollout_observation_impact > 0:
        signals.append(
            _upsert_signal(
                snapshot=snapshot,
                signal_type=CampaignAttentionSignalType.ROLLOUT_WARNING,
                severity=CampaignAttentionSeverity.MEDIUM,
                rationale='Rollout observation signals caution for active campaign steps.',
                reason_codes=['ROLLOUT_WARNING'],
                blockers=snapshot.blockers,
            )
        )

    return signals
