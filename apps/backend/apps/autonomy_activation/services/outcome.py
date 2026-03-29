from __future__ import annotations

from django.utils import timezone

from apps.autonomy_activation.models import CampaignActivation, CampaignActivationStatus
from apps.autonomy_launch.models import LaunchAuthorizationStatus


def create_activation_record(*, campaign, authorization, trigger_source: str, rationale: str, actor: str, metadata: dict | None = None) -> CampaignActivation:
    return CampaignActivation.objects.create(
        campaign=campaign,
        launch_authorization=authorization,
        trigger_source=trigger_source,
        activation_status=CampaignActivationStatus.DISPATCHING,
        dispatch_rationale=rationale,
        activated_by=actor,
        metadata=metadata or {},
    )


def mark_activation_blocked(*, activation: CampaignActivation, reason_codes: list[str], blockers: list[str], status: str = CampaignActivationStatus.BLOCKED) -> CampaignActivation:
    activation.activation_status = status
    activation.reason_codes = reason_codes
    activation.blockers = blockers
    activation.save(update_fields=['activation_status', 'reason_codes', 'blockers', 'updated_at'])
    return activation


def mark_activation_failed(*, activation: CampaignActivation, failure_message: str, reason_codes: list[str], blockers: list[str]) -> CampaignActivation:
    activation.activation_status = CampaignActivationStatus.FAILED
    activation.failure_message = failure_message
    activation.reason_codes = reason_codes
    activation.blockers = blockers
    activation.save(update_fields=['activation_status', 'failure_message', 'reason_codes', 'blockers', 'updated_at'])
    return activation


def mark_activation_started(*, activation: CampaignActivation, campaign_status: str) -> CampaignActivation:
    activation.activation_status = CampaignActivationStatus.STARTED
    activation.started_campaign_state = campaign_status
    activation.activated_at = timezone.now()
    activation.save(update_fields=['activation_status', 'started_campaign_state', 'activated_at', 'updated_at'])

    if activation.launch_authorization_id:
        launch_auth = activation.launch_authorization
        launch_auth.authorization_status = LaunchAuthorizationStatus.EXPIRED
        launch_auth.metadata = {
            **(launch_auth.metadata or {}),
            'consumed_by_activation_id': activation.id,
            'consumed_at': activation.activated_at.isoformat(),
        }
        launch_auth.save(update_fields=['authorization_status', 'metadata', 'updated_at'])

    return activation
