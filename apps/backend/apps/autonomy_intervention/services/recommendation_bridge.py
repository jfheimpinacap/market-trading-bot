from apps.autonomy_intervention.models import InterventionRequestedAction


RECOMMENDATION_TO_ACTION = {
    'PAUSE_CAMPAIGN': InterventionRequestedAction.PAUSE_CAMPAIGN,
    'RESUME_CAMPAIGN': InterventionRequestedAction.RESUME_CAMPAIGN,
    'ESCALATE_TO_APPROVAL': InterventionRequestedAction.ESCALATE_TO_APPROVAL,
    'REVIEW_FOR_ABORT': InterventionRequestedAction.REVIEW_FOR_ABORT,
    'CLEAR_TO_CONTINUE': InterventionRequestedAction.CLEAR_TO_CONTINUE,
}


def map_recommendation_to_action(recommendation_type: str) -> str | None:
    return RECOMMENDATION_TO_ACTION.get(recommendation_type)
