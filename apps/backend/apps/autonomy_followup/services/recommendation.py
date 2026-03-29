from __future__ import annotations

from apps.autonomy_followup.models import FollowupRecommendationType, FollowupType
from apps.autonomy_followup.services.candidates import FollowupCandidate


def build_candidate_recommendations(candidate: FollowupCandidate) -> list[dict]:
    rows: list[dict] = []
    if candidate.followup_readiness == 'BLOCKED':
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.REQUIRE_MANUAL_REVIEW,
                'followup_type': '',
                'rationale': 'Critical closeout prerequisites are missing; keep manual-first review.',
                'reason_codes': ['missing_closeout_prerequisites'],
                'confidence': 0.95,
                'blockers': candidate.blockers,
            }
        )
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.KEEP_PENDING,
                'followup_type': '',
                'rationale': 'Follow-up should remain pending until blockers are cleared.',
                'reason_codes': ['keep_pending'],
                'confidence': 0.9,
                'blockers': candidate.blockers,
            }
        )
        return rows

    if candidate.followup_readiness == 'ALREADY_EMITTED':
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.SKIP_DUPLICATE_FOLLOWUP,
                'followup_type': '',
                'rationale': 'Required follow-up artifacts are already linked to closeout.',
                'reason_codes': ['already_emitted'],
                'confidence': 0.99,
                'blockers': [],
            }
        )
        return rows

    if candidate.requires_postmortem:
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.EMIT_POSTMORTEM_REQUEST,
                'followup_type': FollowupType.POSTMORTEM_REQUEST,
                'rationale': 'Closeout indicates incident/failure pressure that should open formal board review.',
                'reason_codes': ['incident_pressure'],
                'confidence': 0.9,
                'blockers': [],
            }
        )
    if candidate.requires_memory_index:
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.EMIT_MEMORY_INDEX,
                'followup_type': FollowupType.MEMORY_INDEX,
                'rationale': 'Stable final outcome can be indexed as reusable memory precedent.',
                'reason_codes': ['stable_outcome'],
                'confidence': 0.85,
                'blockers': [],
            }
        )
    if candidate.requires_roadmap_feedback:
        rows.append(
            {
                'recommendation_type': FollowupRecommendationType.EMIT_ROADMAP_FEEDBACK,
                'followup_type': FollowupType.ROADMAP_FEEDBACK,
                'rationale': 'Campaign friction should be routed to roadmap/scenario feedback artifacts.',
                'reason_codes': ['dependency_or_sequence_friction'],
                'confidence': 0.8,
                'blockers': [],
            }
        )

    return rows
