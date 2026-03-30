from __future__ import annotations

from apps.promotion_committee.models import (
    AdoptionActionCandidate,
    AdoptionTargetResolutionStatus,
    PromotionAdoptionRun,
    PromotionCase,
    PromotionCaseStatus,
)


def build_adoption_candidates(*, adoption_run: PromotionAdoptionRun):
    approved_cases = PromotionCase.objects.filter(case_status=PromotionCaseStatus.APPROVED_FOR_MANUAL_ADOPTION).order_by('-created_at', '-id')
    candidates: list[AdoptionActionCandidate] = []

    for case in approved_cases:
        defaults = {
            'adoption_run': adoption_run,
            'target_component': case.target_component,
            'target_scope': case.target_scope,
            'change_type': case.change_type,
            'current_value': case.current_value,
            'proposed_value': case.proposed_value,
            'target_resolution_status': AdoptionTargetResolutionStatus.UNKNOWN,
            'ready_for_action': False,
            'blockers': list(case.blockers or []),
            'metadata': {'source': 'promotion_case', **(case.metadata or {})},
        }
        candidate, created = AdoptionActionCandidate.objects.get_or_create(linked_promotion_case=case, defaults=defaults)
        if not created:
            candidate.adoption_run = adoption_run
            candidate.current_value = case.current_value
            candidate.proposed_value = case.proposed_value
            candidate.blockers = list(case.blockers or [])
            candidate.metadata = {**(candidate.metadata or {}), 'refreshed_by_run': adoption_run.id}
            candidate.save(update_fields=['adoption_run', 'current_value', 'proposed_value', 'blockers', 'metadata', 'updated_at'])
        candidates.append(candidate)

    return candidates
