from apps.autonomy_intervention.models import InterventionRequestedAction


def recommendation_to_requested_action(recommendation_type: str | None) -> str | None:
    mapping = {
        'PAUSE_CAMPAIGN': InterventionRequestedAction.PAUSE_CAMPAIGN,
        'RESUME_CAMPAIGN': InterventionRequestedAction.RESUME_CAMPAIGN,
        'ESCALATE_TO_APPROVAL': InterventionRequestedAction.ESCALATE_TO_APPROVAL,
        'REVIEW_FOR_ABORT': InterventionRequestedAction.REVIEW_FOR_ABORT,
        'CLEAR_TO_CONTINUE': InterventionRequestedAction.CLEAR_TO_CONTINUE,
    }
    return mapping.get((recommendation_type or '').upper())


def requested_action_to_action_type(requested_action: str) -> str:
    mapping = {
        InterventionRequestedAction.PAUSE_CAMPAIGN: 'pause',
        InterventionRequestedAction.RESUME_CAMPAIGN: 'resume',
        InterventionRequestedAction.ESCALATE_TO_APPROVAL: 'escalate',
        InterventionRequestedAction.REVIEW_FOR_ABORT: 'abort_review',
        InterventionRequestedAction.CLEAR_TO_CONTINUE: 'continue_clearance',
    }
    return mapping[requested_action]
