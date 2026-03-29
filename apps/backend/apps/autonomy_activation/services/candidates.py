from __future__ import annotations

from django.utils import timezone

from apps.autonomy_activation.services.revalidation import revalidate_campaign_dispatch
from apps.autonomy_campaign.models import AutonomyCampaign
from apps.autonomy_launch.models import LaunchAuthorization, LaunchAuthorizationStatus
from apps.autonomy_program.models import AutonomyProgramState
from apps.autonomy_program.services.state import recompute_program_state
from apps.autonomy_scheduler.services.windows import get_active_window, resolve_window_status


def _latest_authorization_by_campaign(campaign_ids: list[int]) -> dict[int, LaunchAuthorization]:
    rows = (
        LaunchAuthorization.objects.select_related('approved_request')
        .filter(campaign_id__in=campaign_ids)
        .order_by('campaign_id', '-created_at', '-id')
    )
    result: dict[int, LaunchAuthorization] = {}
    for row in rows:
        result.setdefault(row.campaign_id, row)
    return result


def build_activation_candidates() -> list[dict]:
    campaigns = list(
        AutonomyCampaign.objects.filter(launch_authorizations__authorization_status=LaunchAuthorizationStatus.AUTHORIZED)
        .distinct()
        .order_by('-created_at', '-id')
    )
    if not campaigns:
        return []

    state = AutonomyProgramState.objects.order_by('-created_at', '-id').first() or recompute_program_state()
    window = get_active_window()
    window_status = resolve_window_status(window) if window else 'CLOSED'
    auth_map = _latest_authorization_by_campaign([campaign.id for campaign in campaigns])

    now = timezone.now()
    output: list[dict] = []
    for campaign in campaigns:
        auth = auth_map.get(campaign.id)
        if auth and auth.expires_at and auth.expires_at <= now and auth.authorization_status != LaunchAuthorizationStatus.EXPIRED:
            auth.authorization_status = LaunchAuthorizationStatus.EXPIRED
            auth.metadata = {**(auth.metadata or {}), 'expired_by': 'autonomy_activation_candidates'}
            auth.save(update_fields=['authorization_status', 'metadata', 'updated_at'])

        validation = revalidate_campaign_dispatch(
            campaign=campaign,
            authorization=auth,
            program_posture=state.concurrency_posture,
            active_window_status=window_status,
            locked_domains=state.locked_domains,
        )

        output.append(
            {
                'campaign': campaign,
                'launch_authorization': auth,
                'authorization_status': auth.authorization_status if auth else 'MISSING',
                'expires_at': auth.expires_at if auth else None,
                'current_program_posture': state.concurrency_posture,
                'active_window': window,
                'domain_conflict': validation.domain_conflict,
                'incident_impact': validation.incident_impact,
                'degraded_impact': validation.degraded_impact,
                'rollout_pressure': validation.rollout_pressure,
                'dispatch_readiness_status': validation.readiness_status,
                'blockers': validation.blockers,
                'metadata': {
                    'reason_codes': validation.reason_codes,
                    'campaign_status': campaign.status,
                    'window_status': window_status,
                },
            }
        )

    return sorted(output, key=lambda item: (0 if item['dispatch_readiness_status'] == 'READY_TO_DISPATCH' else 1, -(item['campaign'].created_at.timestamp())))
