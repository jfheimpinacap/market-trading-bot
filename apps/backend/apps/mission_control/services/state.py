from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.mission_control.models import MissionControlState
from apps.mission_control.services.profiles import DEFAULT_PROFILE


@transaction.atomic
def get_or_create_state() -> MissionControlState:
    state = MissionControlState.objects.select_for_update().first()
    if state is None:
        state = MissionControlState.objects.create(
            profile_slug=DEFAULT_PROFILE['slug'],
            settings_snapshot=DEFAULT_PROFILE,
            status='IDLE',
        )
    elif not state.settings_snapshot:
        state.settings_snapshot = DEFAULT_PROFILE
        state.save(update_fields=['settings_snapshot', 'updated_at'])
    return state


def heartbeat(*, error: str = '') -> None:
    with transaction.atomic():
        state = get_or_create_state()
        state.last_heartbeat_at = timezone.now()
        if error:
            state.last_error = error
        state.save(update_fields=['last_heartbeat_at', 'last_error', 'updated_at'])
