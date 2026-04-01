from __future__ import annotations

from django.utils import timezone

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseCaseStatus,
    DownstreamLifecycleOutcomeType,
    ResponseCaseResolution,
    ResponseCaseResolutionStatus,
    ResponseCaseResolutionType,
    ResponseCaseDownstreamStatus,
)
from apps.certification_board.services.baseline_response_actions.tracking import create_tracking_record
from apps.certification_board.services.baseline_response_resolution.references import create_manual_reference


def derive_resolution(*, candidate) -> tuple[str, str, str, list[str], list[str]]:
    outcome = candidate.latest_lifecycle_outcome
    routing_target = (candidate.linked_routing_action.routing_target if candidate.linked_routing_action else '').lower()
    ref = (outcome.linked_target_reference if outcome else '') or ''
    ref_lower = ref.lower()

    if not candidate.ready_for_resolution:
        return (
            ResponseCaseResolutionType.DEFERRED_WAITING_EVIDENCE,
            ResponseCaseResolutionStatus.PROPOSED,
            'Case is not ready for formal closure yet; waiting for evidence or downstream completion.',
            ['waiting_evidence'],
            candidate.blockers,
        )
    if outcome and outcome.outcome_type == DownstreamLifecycleOutcomeType.NO_ACTION_TAKEN:
        return (ResponseCaseResolutionType.CLOSED_NO_ACTION, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Downstream review indicates no additional action is required.', ['downstream_no_action'], [])
    if 'tuning' in ref_lower or 'tuning' in routing_target:
        return (ResponseCaseResolutionType.RESOLVED_BY_TUNING_REVIEW, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Downstream tuning review evidence is available for closure.', ['tuning_review_reference'], [])
    if 'monitor' in ref_lower or 'monitoring' in routing_target:
        return (ResponseCaseResolutionType.RESOLVED_BY_MONITORING_ONLY, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Case completed with monitoring-only evidence and no additional intervention.', ['monitoring_decision'], [])
    if 'eval' in ref_lower or 'reeval' in ref_lower or 'evaluation' in routing_target:
        return (ResponseCaseResolutionType.RESOLVED_BY_REEVALUATION, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Reevaluation outcome is available to support closure.', ['reevaluation_reference'], [])
    if 'rollback' in ref_lower or 'rollback' in routing_target:
        return (ResponseCaseResolutionType.RESOLVED_BY_ROLLBACK_REVIEW, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Rollback review evidence is available for closure.', ['rollback_review_reference'], [])
    if outcome and outcome.outcome_type == DownstreamLifecycleOutcomeType.REJECTED_BY_TARGET:
        return (ResponseCaseResolutionType.CLOSED_NO_ACTION, ResponseCaseResolutionStatus.READY_TO_CLOSE, 'Case was rejected downstream and can be closed with no action.', ['rejected_by_target'], [])
    return (ResponseCaseResolutionType.ESCALATED_FOR_MANUAL_REVIEW, ResponseCaseResolutionStatus.PROPOSED, 'Outcome is ambiguous and requires manual review before closure.', ['ambiguous_outcome'], ['requires_manual_review'])


def upsert_proposed_resolution(*, candidate):
    res_type, res_status, rationale, reason_codes, blockers = derive_resolution(candidate=candidate)
    resolution = ResponseCaseResolution.objects.filter(
        linked_response_case=candidate.linked_response_case,
        resolution_status__in=[ResponseCaseResolutionStatus.PROPOSED, ResponseCaseResolutionStatus.READY_TO_CLOSE],
    ).order_by('-created_at', '-id').first()
    if resolution is None:
        resolution = ResponseCaseResolution(linked_response_case=candidate.linked_response_case)
    resolution.linked_candidate = candidate
    resolution.resolution_type = res_type
    resolution.resolution_status = res_status
    resolution.rationale = rationale
    resolution.reason_codes = reason_codes
    resolution.blockers = blockers
    resolution.metadata = {'source': 'baseline-response-resolution-run'}
    resolution.save()
    return resolution


def resolve_response_case_manually(*, response_case: BaselineResponseCase, payload: dict) -> ResponseCaseResolution:
    resolution, _ = ResponseCaseResolution.objects.get_or_create(
        linked_response_case=response_case,
        defaults={
            'resolution_type': payload['resolution_type'],
            'resolution_status': ResponseCaseResolutionStatus.RESOLVED,
        },
    )
    resolution.resolution_type = payload['resolution_type']
    resolution.resolution_status = payload.get('resolution_status') or ResponseCaseResolutionStatus.RESOLVED
    resolution.rationale = payload.get('rationale', '')
    resolution.reason_codes = payload.get('reason_codes') or []
    resolution.blockers = payload.get('blockers') or []
    resolution.resolved_by = payload.get('resolved_by', 'operator-ui')
    resolution.resolved_at = timezone.now()
    resolution.metadata = {**(resolution.metadata or {}), **(payload.get('metadata') or {}), 'manual_resolve': True}
    resolution.save()

    if resolution.resolution_status == ResponseCaseResolutionStatus.RESOLVED:
        case_status = BaselineResponseCaseStatus.ROUTED
        tracking_status = ResponseCaseDownstreamStatus.COMPLETED
        if resolution.resolution_type == ResponseCaseResolutionType.CLOSED_NO_ACTION:
            case_status = BaselineResponseCaseStatus.CLOSED_NO_ACTION
            tracking_status = ResponseCaseDownstreamStatus.CLOSED_NO_ACTION
        elif resolution.resolution_type == ResponseCaseResolutionType.ESCALATED_FOR_MANUAL_REVIEW:
            case_status = BaselineResponseCaseStatus.ESCALATED
            tracking_status = ResponseCaseDownstreamStatus.ESCALATED

        response_case.case_status = case_status
        response_case.save(update_fields=['case_status', 'updated_at'])

        action = response_case.routing_actions.order_by('-created_at', '-id').first()
        create_tracking_record(
            response_case=response_case,
            routing_action=action,
            downstream_status=tracking_status,
            tracking_notes=payload.get('tracking_notes') or 'Case resolved manually with formal resolution record.',
            tracked_by=resolution.resolved_by,
            linked_downstream_reference=payload.get('linked_downstream_reference', ''),
            metadata={'source': 'resolve-response-case', **(payload.get('metadata') or {})},
        )

    manual_reference = payload.get('downstream_reference')
    if manual_reference:
        create_manual_reference(resolution=resolution, payload=manual_reference)

    return resolution
