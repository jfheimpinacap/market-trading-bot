from decimal import Decimal

from apps.autonomy_program.services.state import build_program_state_payload
from apps.autonomy_scheduler.models import AdmissionRecommendation, AdmissionRecommendationType, CampaignAdmissionStatus, SchedulerRun
from apps.autonomy_scheduler.services.admission import evaluate_admission
from apps.autonomy_scheduler.services.prioritization import prioritize
from apps.autonomy_scheduler.services.queue import ensure_campaign_admissions, queue_counts
from apps.autonomy_scheduler.services.windows import get_active_window


def run_scheduler_plan(*, actor: str = 'operator-ui') -> dict:
    state_payload = build_program_state_payload()
    state = state_payload['state']
    rows = ensure_campaign_admissions()
    window = get_active_window()
    max_starts = window.max_new_admissions if window else 0
    if state.concurrency_posture == 'HIGH_RISK':
        max_starts = min(max_starts, 1)
    elif state.concurrency_posture == 'FROZEN':
        max_starts = 0

    prioritized = prioritize(rows)
    evaluations = [
        (admission, evaluate_admission(admission, active_window=window, critical_incident_active=state_payload['critical_incident_active'], locked_domains=state.locked_domains))
        for admission in prioritized
    ]
    ready = [a for a, _ in evaluations if a.status == CampaignAdmissionStatus.READY]
    blocked = [a for a, _ in evaluations if a.status == CampaignAdmissionStatus.BLOCKED]
    deferred = [a for a, _ in evaluations if a.status == CampaignAdmissionStatus.DEFERRED]

    run = SchedulerRun.objects.create(
        queue_counts=queue_counts(prioritized),
        ready_campaigns=[item.campaign_id for item in ready],
        blocked_campaigns=[item.campaign_id for item in blocked],
        deferred_campaigns=[item.campaign_id for item in deferred],
        current_program_posture=state.concurrency_posture,
        active_window=window,
        max_admissible_starts=max_starts,
        recommendations_summary={'ready': len(ready), 'blocked': len(blocked), 'deferred': len(deferred), 'actor': actor},
        metadata={'critical_incident_active': state_payload['critical_incident_active'], 'conflicts': state_payload['conflicts']},
    )

    recs = []
    if not window or window.status != 'OPEN':
        recs.append(
            AdmissionRecommendation.objects.create(
                scheduler_run=run,
                recommendation_type=AdmissionRecommendationType.WAIT_FOR_WINDOW,
                rationale='No open safe-start window is available for admissions.',
                reason_codes=['WAIT_FOR_WINDOW'],
                confidence=Decimal('0.9800'),
                blockers=['window_closed_or_missing'],
                impacted_domains=[],
                recommended_window=window,
            )
        )
    if state.concurrency_posture in ['FROZEN', 'HIGH_RISK']:
        recs.append(
            AdmissionRecommendation.objects.create(
                scheduler_run=run,
                recommendation_type=AdmissionRecommendationType.BLOCK_ADMISSION,
                rationale='Program posture restricts new admissions.',
                reason_codes=[f'PROGRAM_{state.concurrency_posture}'],
                confidence=Decimal('0.9700'),
                blockers=[state.concurrency_posture],
                impacted_domains=state.locked_domains,
                recommended_window=window,
            )
        )

    if len(ready) > max_starts and max_starts > 0:
        recs.append(
            AdmissionRecommendation.objects.create(
                scheduler_run=run,
                recommendation_type=AdmissionRecommendationType.REORDER_ADMISSION_QUEUE,
                rationale='Ready candidates exceed current safe-start capacity; apply ranked queue order.',
                reason_codes=['CAPACITY_CONFLICT'],
                confidence=Decimal('0.9000'),
                blockers=[],
                impacted_domains=[],
                recommended_window=window,
                metadata={'ordered_campaign_ids': [item.campaign_id for item in ready]},
            )
        )

    if ready and max_starts > 0 and (not window or window.status == 'OPEN') and state.concurrency_posture not in ['FROZEN']:
        best = ready[0]
        requires_approval = best.priority_score >= 80 and state.concurrency_posture in ['CONSTRAINED', 'HIGH_RISK']
        rec_type = AdmissionRecommendationType.REQUIRE_APPROVAL_TO_ADMIT if requires_approval else AdmissionRecommendationType.SAFE_TO_ADMIT_NEXT
        recs.append(
            AdmissionRecommendation.objects.create(
                scheduler_run=run,
                recommendation_type=rec_type,
                target_campaign=best.campaign,
                rationale='Top ranked campaign is ready for controlled manual admission.' if not requires_approval else 'Campaign is ready but should be admitted only after approval due to posture/impact.',
                reason_codes=['TOP_PRIORITY_READY'] if not requires_approval else ['APPROVAL_REQUIRED_FOR_ADMISSION'],
                confidence=Decimal('0.8600'),
                blockers=[] if not requires_approval else ['approval_required'],
                impacted_domains=best.campaign.metadata.get('domains', []) if isinstance(best.campaign.metadata, dict) else [],
                recommended_window=window,
            )
        )

    return {'run': run, 'recommendations': recs, 'queue': prioritized, 'window': window}
