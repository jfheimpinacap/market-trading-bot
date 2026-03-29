<<<<<<< HEAD
from apps.autonomy_intervention.models import InterventionOutcome


def persist_outcome(*, action, outcome_type: str, campaign_state_before: str, campaign_state_after: str, summary: str, metadata: dict | None = None):
=======
from __future__ import annotations

from django.utils import timezone

from apps.autonomy_intervention.models import InterventionOutcome, InterventionOutcomeType


def record_outcome(*, action, outcome_type: str, campaign_state_before: str, campaign_state_after: str, summary: str, metadata=None):
    action.result_summary = summary
    action.executed_at = timezone.now()
    action.save(update_fields=['result_summary', 'executed_at', 'updated_at'])
>>>>>>> origin/main
    return InterventionOutcome.objects.create(
        action=action,
        outcome_type=outcome_type,
        campaign_state_before=campaign_state_before,
        campaign_state_after=campaign_state_after,
        summary=summary,
        metadata=metadata or {},
    )
<<<<<<< HEAD
=======


def blocked_outcome(action, before: str, summary: str, blockers: list[str]):
    return record_outcome(
        action=action,
        outcome_type=InterventionOutcomeType.ACTION_BLOCKED,
        campaign_state_before=before,
        campaign_state_after=before,
        summary=summary,
        metadata={'blockers': blockers},
    )
>>>>>>> origin/main
