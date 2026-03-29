from apps.autonomy_intervention.models import InterventionOutcome


def persist_outcome(*, action, outcome_type: str, campaign_state_before: str, campaign_state_after: str, summary: str, metadata: dict | None = None):
    return InterventionOutcome.objects.create(
        action=action,
        outcome_type=outcome_type,
        campaign_state_before=campaign_state_before,
        campaign_state_after=campaign_state_after,
        summary=summary,
        metadata=metadata or {},
    )
