from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.automation_policy.models import AutomationPolicyRule
from apps.autonomy_manager.models import AutonomyDomain, AutonomyStageTransition, AutonomyTransitionStatus
from apps.certification_board.models import CertificationRun
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.policy_rollout.models import PolicyRolloutRecommendationCode, PolicyRolloutRecommendation
from apps.trust_calibration.models import (
    TrustCalibrationRecommendation,
    TrustCalibrationRecommendationType,
    TrustCalibrationRun,
)


@dataclass
class DomainEvidence:
    domain: AutonomyDomain
    trust_promote: int
    trust_downgrade: int
    trust_require_more_data: int
    rollout_rollback_recommended: int
    incidents_high: int
    approvals_pending: int
    auto_success_rate: float
    rollback_history: int
    certification_constrained: bool
    sample_size: int
    evidence_refs: list[dict]


def _latest_trust_run() -> TrustCalibrationRun | None:
    return TrustCalibrationRun.objects.order_by('-started_at', '-id').first()


def _latest_certification_constrained() -> tuple[bool, dict | None]:
    latest = CertificationRun.objects.order_by('-created_at', '-id').first()
    if not latest:
        return False, None
    constrained = latest.certification_level in {
        'RECERTIFICATION_REQUIRED',
        'REMEDIATION_REQUIRED',
    }
    return constrained, {'type': 'certification_run', 'id': latest.id, 'certification_level': latest.certification_level}


def collect_domain_evidence(domain: AutonomyDomain) -> DomainEvidence:
    action_types = list(domain.action_types or [])
    source_apps = list(domain.source_apps or [])

    trust_run = _latest_trust_run()
    trust_recommendations = TrustCalibrationRecommendation.objects.none()
    if trust_run and action_types:
        trust_recommendations = TrustCalibrationRecommendation.objects.filter(run=trust_run, action_type__in=action_types)

    promote_count = trust_recommendations.filter(
        recommendation_type__in=[
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
            TrustCalibrationRecommendationType.KEEP_APPROVAL_REQUIRED,
        ]
    ).count()
    downgrade_count = trust_recommendations.filter(
        recommendation_type__in=[
            TrustCalibrationRecommendationType.DOWNGRADE_TO_MANUAL_ONLY,
            TrustCalibrationRecommendationType.BLOCK_AUTOMATION_FOR_ACTION,
        ]
    ).count()
    require_more_data = trust_recommendations.filter(recommendation_type=TrustCalibrationRecommendationType.REQUIRE_MORE_DATA).count()

    success_values = [
        float(rec.supporting_metrics.get('auto_execution_success_rate') or rec.supporting_metrics.get('auto_action_success_rate') or 0)
        for rec in trust_recommendations
    ]
    auto_success_rate = mean(success_values) if success_values else 0

    rollout_recommendations = PolicyRolloutRecommendation.objects.filter(
        run__policy_tuning_candidate__action_type__in=action_types,
        recommendation=PolicyRolloutRecommendationCode.ROLLBACK_CHANGE,
    ) if action_types else PolicyRolloutRecommendation.objects.none()

    incident_qs = IncidentRecord.objects.filter(status__in=[IncidentStatus.OPEN, IncidentStatus.DEGRADED, IncidentStatus.ESCALATED])
    if source_apps:
        incident_qs = incident_qs.filter(source_app__in=source_apps)
    incidents_high = incident_qs.filter(severity__in=[IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]).count()

    approvals_pending = ApprovalRequest.objects.filter(status=ApprovalRequestStatus.PENDING).count()

    rollback_history = AutonomyStageTransition.objects.filter(domain=domain, status=AutonomyTransitionStatus.ROLLED_BACK).count()
    constrained, certification_ref = _latest_certification_constrained()

    refs: list[dict] = []
    if trust_run:
        refs.append({'type': 'trust_calibration_run', 'id': trust_run.id})
    latest_rollout = rollout_recommendations.order_by('-created_at', '-id').first()
    if latest_rollout:
        refs.append({'type': 'policy_rollout_run', 'id': latest_rollout.run_id})
    latest_incident = incident_qs.order_by('-last_seen_at', '-id').first()
    if latest_incident:
        refs.append({'type': 'incident', 'id': latest_incident.id})
    if certification_ref:
        refs.append(certification_ref)
    if approvals_pending:
        refs.append({'type': 'approval_queue', 'pending': approvals_pending})

    return DomainEvidence(
        domain=domain,
        trust_promote=promote_count,
        trust_downgrade=downgrade_count,
        trust_require_more_data=require_more_data,
        rollout_rollback_recommended=rollout_recommendations.count(),
        incidents_high=incidents_high,
        approvals_pending=approvals_pending,
        auto_success_rate=auto_success_rate,
        rollback_history=rollback_history,
        certification_constrained=constrained,
        sample_size=trust_recommendations.count(),
        evidence_refs=refs,
    )


def resolve_linked_policy_profiles(domain: AutonomyDomain) -> list[str]:
    return sorted(
        set(
            AutomationPolicyRule.objects.filter(action_type__in=list(domain.action_types or []))
            .values_list('profile__slug', flat=True)
        )
    )
