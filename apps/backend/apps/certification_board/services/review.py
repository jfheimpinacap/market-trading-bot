from apps.certification_board.models import CertificationDecisionLog, CertificationRun, CertificationRunStatus
from apps.certification_board.services.envelope import build_operating_envelope
from apps.certification_board.services.evidence import build_evidence_snapshot
from apps.certification_board.services.recommendation import generate_recommendation


def run_certification_review(*, decision_mode: str = 'RECOMMENDATION_ONLY', metadata: dict | None = None) -> CertificationRun:
    snapshot = build_evidence_snapshot(metadata=metadata)
    recommendation = generate_recommendation(snapshot)
    envelope = build_operating_envelope(level=recommendation.level, snapshot=snapshot)

    run = CertificationRun.objects.create(
        status=CertificationRunStatus.COMPLETED,
        decision_mode=decision_mode,
        certification_level=recommendation.level,
        recommendation_code=recommendation.code,
        confidence=recommendation.confidence,
        rationale=recommendation.rationale,
        reason_codes=recommendation.reason_codes,
        blocking_constraints=recommendation.blocking_constraints,
        remediation_items=recommendation.remediation_items,
        evidence_summary=recommendation.evidence_summary,
        summary=f"{recommendation.level}: {recommendation.rationale}",
        evidence_snapshot=snapshot,
        operating_envelope=envelope,
        metadata=metadata or {},
    )
    CertificationDecisionLog.objects.create(
        run=run,
        event_type='RECOMMENDATION_ISSUED',
        actor='certification_board',
        notes='Operational certification recommendation generated from consolidated evidence.',
        payload={
            'certification_level': recommendation.level,
            'recommendation_code': recommendation.code,
            'reason_codes': recommendation.reason_codes,
        },
    )
    return run


def get_current_certification() -> CertificationRun | None:
    return CertificationRun.objects.select_related('evidence_snapshot', 'operating_envelope').prefetch_related('decision_logs').order_by('-created_at', '-id').first()


def build_certification_summary() -> dict:
    latest_run = get_current_certification()
    runs = CertificationRun.objects.order_by('-created_at', '-id')[:20]
    total = CertificationRun.objects.count()

    level_counts: dict[str, int] = {}
    recommendation_counts: dict[str, int] = {}
    for item in runs:
        level_counts[item.certification_level] = level_counts.get(item.certification_level, 0) + 1
        recommendation_counts[item.recommendation_code] = recommendation_counts.get(item.recommendation_code, 0) + 1

    return {
        'latest_run': latest_run,
        'recent_runs': runs,
        'total_runs': total,
        'level_counts': level_counts,
        'recommendation_counts': recommendation_counts,
    }
