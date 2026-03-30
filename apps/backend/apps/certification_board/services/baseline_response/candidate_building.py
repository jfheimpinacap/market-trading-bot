from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineHealthStatus,
    BaselineHealthStatusCode,
    BaselineResponseCase,
    BaselineResponseCaseStatus,
    BaselineResponsePriority,
    BaselineResponseRun,
    BaselineResponseType,
)


def _priority_from_status(health_status: BaselineHealthStatus, response_type: str) -> str:
    if response_type == BaselineResponseType.PREPARE_ROLLBACK_REVIEW:
        return BaselineResponsePriority.CRITICAL
    if response_type in {
        BaselineResponseType.REQUIRE_MANUAL_BASELINE_REVIEW,
        BaselineResponseType.OPEN_TUNING_REVIEW,
    }:
        return BaselineResponsePriority.HIGH
    if response_type == BaselineResponseType.OPEN_REEVALUATION:
        return BaselineResponsePriority.MEDIUM

    has_high_signal = health_status.signals.filter(signal_severity__in=['HIGH', 'CRITICAL']).exists()
    return BaselineResponsePriority.MEDIUM if has_high_signal else BaselineResponsePriority.LOW


def determine_response_type(status: BaselineHealthStatus) -> str | None:
    signal_count = status.signals.count()
    critical_signal_count = status.signals.filter(signal_severity='CRITICAL').count()
    sample_count = int((status.metadata or {}).get('sample_count') or 0)

    if status.health_status == BaselineHealthStatusCode.HEALTHY:
        if critical_signal_count > 0:
            return BaselineResponseType.REQUIRE_COMMITTEE_RECHECK
        return None

    if status.health_status == BaselineHealthStatusCode.INSUFFICIENT_DATA:
        return BaselineResponseType.KEEP_UNDER_WATCH

    if status.health_status == BaselineHealthStatusCode.UNDER_WATCH:
        if sample_count < 12 or signal_count <= 1:
            return BaselineResponseType.KEEP_UNDER_WATCH
        return BaselineResponseType.OPEN_REEVALUATION

    if status.health_status == BaselineHealthStatusCode.DEGRADED:
        if sample_count < 12:
            return BaselineResponseType.OPEN_REEVALUATION
        return BaselineResponseType.OPEN_TUNING_REVIEW if signal_count >= 2 else BaselineResponseType.OPEN_REEVALUATION

    if status.health_status == BaselineHealthStatusCode.REVIEW_REQUIRED:
        if status.linked_candidate.target_scope == 'global':
            return BaselineResponseType.REQUIRE_MANUAL_BASELINE_REVIEW
        return BaselineResponseType.OPEN_TUNING_REVIEW

    if status.health_status == BaselineHealthStatusCode.ROLLBACK_REVIEW_RECOMMENDED:
        return BaselineResponseType.PREPARE_ROLLBACK_REVIEW

    return BaselineResponseType.REQUIRE_COMMITTEE_RECHECK


def build_response_cases(*, review_run: BaselineResponseRun) -> list[BaselineResponseCase]:
    statuses = BaselineHealthStatus.objects.select_related(
        'linked_candidate',
        'linked_candidate__linked_active_binding',
    ).prefetch_related('signals').order_by('-created_at', '-id')[:500]

    cases: list[BaselineResponseCase] = []
    for status in statuses:
        response_type = determine_response_type(status)
        if not response_type:
            continue

        candidate = status.linked_candidate
        signals = [
            {
                'id': signal.id,
                'type': signal.signal_type,
                'severity': signal.signal_severity,
                'direction': signal.signal_direction,
                'rationale': signal.rationale,
            }
            for signal in status.signals.all()
        ]
        reason_codes = list(status.reason_codes or [])
        if response_type == BaselineResponseType.KEEP_UNDER_WATCH and 'monitoring_only' not in reason_codes:
            reason_codes.append('monitoring_only')

        confidence = Decimal('0.55')
        if response_type in {BaselineResponseType.OPEN_TUNING_REVIEW, BaselineResponseType.REQUIRE_MANUAL_BASELINE_REVIEW}:
            confidence = Decimal('0.72')
        if response_type == BaselineResponseType.PREPARE_ROLLBACK_REVIEW:
            confidence = Decimal('0.88')

        cases.append(
            BaselineResponseCase.objects.create(
                review_run=review_run,
                linked_active_binding=candidate.linked_active_binding,
                linked_baseline_health_status=status,
                linked_health_signals=signals,
                target_component=candidate.target_component,
                target_scope=candidate.target_scope,
                response_type=response_type,
                priority_level=_priority_from_status(status, response_type),
                case_status=BaselineResponseCaseStatus.OPEN,
                rationale=status.rationale,
                reason_codes=reason_codes,
                blockers=list(status.blockers or []),
                metadata={
                    'sample_count': int((status.metadata or {}).get('sample_count') or 0),
                    'health_status': status.health_status,
                    'response_confidence': float(confidence),
                    'source_health_run_id': status.linked_candidate.review_run_id,
                },
            )
        )

    return cases
