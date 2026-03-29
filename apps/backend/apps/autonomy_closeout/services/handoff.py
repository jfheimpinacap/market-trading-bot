from __future__ import annotations

from apps.autonomy_closeout.services.candidates import CloseoutCandidate


def build_handoff_plan(candidate: CloseoutCandidate, summary: dict) -> dict:
    memory_payload = {
        'should_index': candidate.requires_memory_index,
        'title': f"Autonomy campaign closeout: {candidate.campaign.title}",
        'source_object_id': str(candidate.campaign.id),
        'tags': ['autonomy_closeout', candidate.disposition.disposition_type.lower()],
        'summary': summary['final_outcome_summary'],
    }
    postmortem_payload = {
        'should_request': candidate.requires_postmortem,
        'campaign_id': candidate.campaign.id,
        'rationale': 'Disposition ended in abort/retire with meaningful incident pressure.' if candidate.requires_postmortem else '',
    }
    roadmap_feedback_payload = {
        'should_prepare': candidate.requires_roadmap_feedback,
        'campaign_id': candidate.campaign.id,
        'reason_codes': ['dependency_conflict_or_intervention_friction'] if candidate.requires_roadmap_feedback else [],
    }
    return {
        'memory_handoff': memory_payload,
        'postmortem_handoff': postmortem_payload,
        'roadmap_feedback_handoff': roadmap_feedback_payload,
    }
