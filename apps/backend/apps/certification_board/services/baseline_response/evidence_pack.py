from __future__ import annotations

from decimal import Decimal

from apps.certification_board.models import (
    BaselineResponseCase,
    BaselineResponseEvidenceStatus,
    ResponseEvidencePack,
)


def _status_from_scores(*, confidence_score: Decimal, severity_score: Decimal, urgency_score: Decimal) -> str:
    composite = (confidence_score + severity_score + urgency_score) / Decimal('3')
    if composite >= Decimal('0.75'):
        return BaselineResponseEvidenceStatus.STRONG
    if composite >= Decimal('0.55'):
        return BaselineResponseEvidenceStatus.MIXED
    if composite >= Decimal('0.35'):
        return BaselineResponseEvidenceStatus.WEAK
    return BaselineResponseEvidenceStatus.INSUFFICIENT


def build_response_evidence_pack(*, response_case: BaselineResponseCase) -> ResponseEvidencePack:
    status = response_case.linked_baseline_health_status
    signal_count = len(response_case.linked_health_signals or [])
    sample_count = int((response_case.metadata or {}).get('sample_count') or 0)

    confidence_score = Decimal('0.30') + min(Decimal('0.5'), Decimal(signal_count) * Decimal('0.1'))
    severity_score = Decimal('0.45')
    urgency_score = Decimal('0.40')

    if status:
        severity_score = max(
            Decimal(status.drift_risk_score),
            Decimal(status.regression_risk_score),
        )
        urgency_score = (Decimal(status.regression_risk_score) + Decimal(status.drift_risk_score)) / Decimal('2')

    if sample_count < 10:
        confidence_score = min(confidence_score, Decimal('0.34'))

    evidence_status = _status_from_scores(
        confidence_score=confidence_score,
        severity_score=severity_score,
        urgency_score=urgency_score,
    )

    return ResponseEvidencePack.objects.create(
        linked_response_case=response_case,
        summary=f"{response_case.target_component}:{response_case.target_scope} -> {response_case.response_type}",
        linked_health_status=status,
        linked_health_signals=list(response_case.linked_health_signals or []),
        linked_evaluation_metrics={'source': 'evaluation_lab', 'available': bool(status)},
        linked_risk_context={'source': 'risk_agent', 'regression_risk_score': str(status.regression_risk_score) if status else '0'},
        linked_opportunity_context={
            'source': 'opportunity_supervisor',
            'opportunity_quality_health_score': str(status.opportunity_quality_health_score) if status else '0',
        },
        confidence_score=confidence_score,
        severity_score=severity_score,
        urgency_score=urgency_score,
        evidence_status=evidence_status,
        metadata={'sample_count': sample_count, 'signal_count': signal_count},
    )
