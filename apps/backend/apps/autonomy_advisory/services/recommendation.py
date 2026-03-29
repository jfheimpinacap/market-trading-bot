from __future__ import annotations

from apps.autonomy_advisory.models import AdvisoryRecommendationType
from .candidates import AdvisoryCandidate


def recommendation_for_candidate(candidate: AdvisoryCandidate) -> dict:
    if candidate.blockers:
        if 'ALREADY_EMITTED' in candidate.blockers:
            return {
                'recommendation_type': AdvisoryRecommendationType.SKIP_DUPLICATE_ADVISORY,
                'artifact_type': candidate.recommendation_type if 'NOTE' in candidate.recommendation_type else '',
                'rationale': 'Equivalent advisory artifact already exists for this insight and target.',
                'reason_codes': ['duplicate_artifact_present'],
                'confidence': '0.9900',
                'blockers': candidate.blockers,
                'metadata': {'candidate': candidate.insight_id},
            }
        return {
            'recommendation_type': AdvisoryRecommendationType.REQUIRE_MANUAL_ADVISORY_REVIEW,
            'artifact_type': candidate.recommendation_type if 'NOTE' in candidate.recommendation_type else '',
            'rationale': 'Candidate is not ready for automated advisory emission due to blockers.',
            'reason_codes': ['manual_review_required'],
            'confidence': '0.6000',
            'blockers': candidate.blockers,
            'metadata': {'candidate': candidate.insight_id},
        }

    mapping = {
        'MEMORY_PRECEDENT_NOTE': AdvisoryRecommendationType.EMIT_MEMORY_PRECEDENT_NOTE,
        'ROADMAP_GOVERNANCE_NOTE': AdvisoryRecommendationType.EMIT_ROADMAP_GOVERNANCE_NOTE,
        'SCENARIO_CAUTION_NOTE': AdvisoryRecommendationType.EMIT_SCENARIO_CAUTION_NOTE,
        'PROGRAM_POLICY_NOTE': AdvisoryRecommendationType.EMIT_PROGRAM_POLICY_NOTE,
        'MANAGER_REVIEW_NOTE': AdvisoryRecommendationType.EMIT_MANAGER_REVIEW_NOTE,
    }
    recommendation_type = mapping.get(candidate.recommendation_type, AdvisoryRecommendationType.REQUIRE_MANUAL_ADVISORY_REVIEW)
    return {
        'recommendation_type': recommendation_type,
        'artifact_type': candidate.recommendation_type,
        'rationale': f'Insight is reviewed and ready to emit {candidate.recommendation_type}.',
        'reason_codes': ['reviewed_ready_for_emission'],
        'confidence': candidate.metadata.get('insight_confidence', '0.7000'),
        'blockers': [],
        'metadata': {'candidate': candidate.insight_id},
    }
