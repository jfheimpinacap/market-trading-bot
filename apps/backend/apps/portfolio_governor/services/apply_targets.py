from __future__ import annotations

from dataclasses import dataclass

from apps.portfolio_governor.models import (
    PortfolioExposureApplyRun,
    PortfolioExposureApplyTarget,
    PortfolioExposureApplyTargetType,
    PortfolioExposureDecision,
    SessionExposureContribution,
)


@dataclass
class ApplyTargetResolution:
    targets: list[PortfolioExposureApplyTarget]
    reason_codes: list[str]


def resolve_apply_targets(*, apply_run: PortfolioExposureApplyRun, decision: PortfolioExposureDecision) -> ApplyTargetResolution:
    contributions = SessionExposureContribution.objects.select_related(
        'linked_session',
        'linked_dispatch_record',
        'linked_cluster_snapshot',
    ).filter(linked_cluster_snapshot=decision.linked_cluster_snapshot)

    targets: list[PortfolioExposureApplyTarget] = []
    reason_codes: list[str] = []
    sessions_seen: set[int] = set()
    dispatches_seen: set[int] = set()

    for contribution in contributions:
        if contribution.linked_session_id and contribution.linked_session_id not in sessions_seen:
            sessions_seen.add(contribution.linked_session_id)
            targets.append(
                PortfolioExposureApplyTarget.objects.create(
                    linked_apply_run=apply_run,
                    linked_exposure_decision=decision,
                    target_type=PortfolioExposureApplyTargetType.SESSION,
                    linked_session=contribution.linked_session,
                    linked_cluster_snapshot=decision.linked_cluster_snapshot,
                    target_summary=f'Session #{contribution.linked_session_id} linked to cluster {decision.linked_cluster_snapshot.cluster_label}.',
                    reason_codes=[contribution.contribution_role.lower(), contribution.contribution_strength.lower()],
                    metadata={'from_contribution_id': contribution.id},
                )
            )
        if contribution.linked_dispatch_record_id and contribution.linked_dispatch_record_id not in dispatches_seen:
            dispatches_seen.add(contribution.linked_dispatch_record_id)
            targets.append(
                PortfolioExposureApplyTarget.objects.create(
                    linked_apply_run=apply_run,
                    linked_exposure_decision=decision,
                    target_type=PortfolioExposureApplyTargetType.PENDING_DISPATCH,
                    linked_dispatch_record=contribution.linked_dispatch_record,
                    linked_cluster_snapshot=decision.linked_cluster_snapshot,
                    target_summary=f'Dispatch #{contribution.linked_dispatch_record_id} can be deferred conservatively.',
                    reason_codes=['pending_dispatch', contribution.contribution_role.lower()],
                    metadata={'from_contribution_id': contribution.id},
                )
            )

    targets.append(
        PortfolioExposureApplyTarget.objects.create(
            linked_apply_run=apply_run,
            linked_exposure_decision=decision,
            target_type=PortfolioExposureApplyTargetType.CLUSTER_GATE,
            linked_cluster_snapshot=decision.linked_cluster_snapshot,
            target_summary=f'Cluster gate for {decision.linked_cluster_snapshot.cluster_label}.',
            reason_codes=['cluster_gate'],
            metadata={'cluster_id': decision.linked_cluster_snapshot_id},
        )
    )

    targets.append(
        PortfolioExposureApplyTarget.objects.create(
            linked_apply_run=apply_run,
            linked_exposure_decision=decision,
            target_type=PortfolioExposureApplyTargetType.ADMISSION_PATH,
            linked_cluster_snapshot=decision.linked_cluster_snapshot,
            target_summary='Admission path can enforce new-entry throttle for this cluster.',
            reason_codes=['admission_path'],
            metadata={'cluster_id': decision.linked_cluster_snapshot_id},
        )
    )

    if not sessions_seen:
        reason_codes.append('no_sessions_found')
    if not dispatches_seen:
        reason_codes.append('no_dispatches_found')

    return ApplyTargetResolution(targets=targets, reason_codes=reason_codes)
