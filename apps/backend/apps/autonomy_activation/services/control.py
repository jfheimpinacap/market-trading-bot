from __future__ import annotations

from django.db import transaction

from apps.autonomy_activation.models import ActivationRun, CampaignActivationStatus, CampaignActivationTriggerSource
from apps.autonomy_activation.services.candidates import build_activation_candidates
from apps.autonomy_activation.services.dispatch import dispatch_campaign_start
from apps.autonomy_activation.services.outcome import (
    create_activation_record,
    mark_activation_blocked,
    mark_activation_failed,
    mark_activation_started,
)
from apps.autonomy_activation.services.recommendation import generate_dispatch_recommendations, summarize_recommendations
from apps.autonomy_activation.services.revalidation import revalidate_campaign_dispatch
from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_program.services.state import recompute_program_state
from apps.autonomy_scheduler.services.windows import get_active_window, resolve_window_status


def run_dispatch_review(*, actor: str = 'operator-ui') -> dict:
    candidates = build_activation_candidates()
    state = AutonomyProgramState.objects.order_by('-created_at', '-id').first() or recompute_program_state()
    window = get_active_window()

    activation_run = ActivationRun.objects.create(
        candidate_count=len(candidates),
        ready_count=sum(1 for item in candidates if item['dispatch_readiness_status'] == 'READY_TO_DISPATCH'),
        blocked_count=sum(1 for item in candidates if item['dispatch_readiness_status'] == 'BLOCKED'),
        expired_count=sum(1 for item in candidates if item['dispatch_readiness_status'] == 'EXPIRED'),
        dispatched_count=0,
        failed_count=0,
        current_program_posture=state.concurrency_posture,
        active_window=window,
        metadata={'actor': actor},
    )

    recs = generate_dispatch_recommendations(candidates=candidates, activation_run=activation_run)
    activation_run.recommendation_summary = summarize_recommendations(recs)
    activation_run.save(update_fields=['recommendation_summary', 'updated_at'])

    return {'run': activation_run, 'candidates': candidates, 'recommendations': recs}


@transaction.atomic
def dispatch_campaign(*, campaign, actor: str = 'operator-ui', trigger_source: str = CampaignActivationTriggerSource.MANUAL_UI, rationale: str = 'Manual dispatch from activation board'):
    initial_campaign_status = campaign.status
    auth = campaign.launch_authorizations.order_by('-created_at', '-id').first()
    state = AutonomyProgramState.objects.order_by('-created_at', '-id').first() or recompute_program_state()
    window = get_active_window()
    window_status = resolve_window_status(window) if window else 'CLOSED'

    activation = create_activation_record(
        campaign=campaign,
        authorization=auth,
        trigger_source=trigger_source,
        rationale=rationale,
        actor=actor,
        metadata={'program_posture': state.concurrency_posture, 'window_status': window_status},
    )

    validation = revalidate_campaign_dispatch(
        campaign=campaign,
        authorization=auth,
        program_posture=state.concurrency_posture,
        active_window_status=window_status,
        locked_domains=state.locked_domains,
    )

    if validation.readiness_status == 'EXPIRED':
        return mark_activation_blocked(
            activation=activation,
            reason_codes=validation.reason_codes,
            blockers=validation.blockers,
            status=CampaignActivationStatus.EXPIRED,
        )

    if validation.readiness_status in {'WAITING', 'BLOCKED'}:
        return mark_activation_blocked(activation=activation, reason_codes=validation.reason_codes, blockers=validation.blockers)

    try:
        started = dispatch_campaign_start(campaign=campaign, actor=actor)
    except Exception as exc:  # noqa: BLE001
        return mark_activation_failed(
            activation=activation,
            failure_message=f'Campaign start failed: {exc}',
            reason_codes=validation.reason_codes + ['CAMPAIGN_START_EXCEPTION'],
            blockers=validation.blockers,
        )

    if started.status == initial_campaign_status:
        return mark_activation_failed(
            activation=activation,
            failure_message='Campaign start returned without entering a startable lifecycle state.',
            reason_codes=validation.reason_codes + ['CAMPAIGN_START_NO_STATE_CHANGE'],
            blockers=validation.blockers,
        )

    return mark_activation_started(activation=activation, campaign_status=started.status)
