from apps.policy_tuning.models import PolicyTuningCandidate


def generate_change_set_diff(candidate: PolicyTuningCandidate) -> dict:
    change_set = candidate.change_set
    return {
        'profile_slug': change_set.profile_slug,
        'action_type': change_set.action_type,
        'trust_tier': {
            'current': change_set.old_trust_tier,
            'proposed': change_set.new_trust_tier,
        },
        'conditions': {
            'current': change_set.old_conditions,
            'proposed': change_set.new_conditions,
        },
        'apply_scope': change_set.apply_scope,
        'notes': change_set.notes,
    }
