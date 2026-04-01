from __future__ import annotations

from apps.autonomous_trader.models import AutonomousFeedbackInfluenceRecord


def build_watch_feedback_patch(*, influence: AutonomousFeedbackInfluenceRecord) -> dict:
    if influence.influence_type in {'CAUTION_BOOST', 'CONFIDENCE_REDUCTION', 'BLOCK_REPEAT_PATTERN'} and influence.influence_status == 'APPLIED':
        return {
            'watch_priority_up': True,
            'exit_review_required_bias': True,
            'memory_context_required': True,
            'linked_influence_record_id': influence.id,
        }
    return {
        'watch_priority_up': False,
        'exit_review_required_bias': False,
        'memory_context_required': False,
        'linked_influence_record_id': influence.id,
    }
