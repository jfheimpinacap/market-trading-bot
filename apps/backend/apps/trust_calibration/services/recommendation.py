from decimal import Decimal

from apps.automation_policy.models import AutomationTrustTier
from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRecommendationType, TrustCalibrationRun


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or '0'))


def _recommend_for_snapshot(snapshot: AutomationFeedbackSnapshot) -> tuple[str, str, str, list[str], Decimal]:
    metrics = snapshot.metrics or {}
    sample_size = int(metrics.get('sample_size') or 0)
    approval_rate = _as_decimal(metrics.get('approval_rate'))
    rejection_rate = _as_decimal(metrics.get('rejection_rate'))
    auto_success = _as_decimal(metrics.get('auto_execution_success_rate'))
    incident_rate = _as_decimal(metrics.get('auto_action_followed_by_incident_rate'))
    friction = _as_decimal(metrics.get('approval_friction_score'))

    current = snapshot.current_trust_tier or AutomationTrustTier.APPROVAL_REQUIRED

    if sample_size < 5:
        return (
            TrustCalibrationRecommendationType.REQUIRE_MORE_DATA,
            current,
            'Not enough approval/autopilot history yet to calibrate trust tiers.',
            ['LOW_SAMPLE_SIZE'],
            Decimal('0.4000'),
        )

    if (approval_rate >= Decimal('0.9000') and rejection_rate <= Decimal('0.1000') and auto_success >= Decimal('0.9000') and incident_rate <= Decimal('0.0500')):
        return (
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
            AutomationTrustTier.SAFE_AUTOMATION,
            'High approval consistency and stable auto-execution suggest this action can move to SAFE_AUTOMATION with manual-first oversight.',
            ['HIGH_APPROVAL_RATE', 'LOW_REJECTION', 'STABLE_AUTOMATION'],
            Decimal('0.8800'),
        )


    if snapshot.incidents_after_auto >= 2 or ((snapshot.auto_actions_failed >= 2 or snapshot.auto_actions_executed >= 3) and (auto_success <= Decimal('0.6500') or incident_rate >= Decimal('0.2500'))):
        target = AutomationTrustTier.MANUAL_ONLY if incident_rate < Decimal('0.4000') else AutomationTrustTier.AUTO_BLOCKED
        rec_type = TrustCalibrationRecommendationType.DOWNGRADE_TO_MANUAL_ONLY if target == AutomationTrustTier.MANUAL_ONLY else TrustCalibrationRecommendationType.BLOCK_AUTOMATION_FOR_ACTION
        return (
            rec_type,
            target,
            'Auto-actions show reversals/incidents above conservative thresholds; downgrade is recommended until remediation is validated.',
            ['AUTOMATION_REVERSAL_RISK', 'INCIDENT_AFTER_AUTO'],
            Decimal('0.9100'),
        )

    if friction >= Decimal('0.5000'):
        return (
            TrustCalibrationRecommendationType.REVIEW_RULE_CONDITIONS,
            current,
            'Approval friction remains high; review rule conditions and runbook checkpoint design before changing trust tier.',
            ['HIGH_FRICTION', 'REVIEW_CONDITIONS'],
            Decimal('0.7300'),
        )

    return (
        TrustCalibrationRecommendationType.KEEP_APPROVAL_REQUIRED,
        AutomationTrustTier.APPROVAL_REQUIRED,
        'Signal is mixed; keep explicit approvals while more history is collected.',
        ['AMBIGUOUS_SIGNAL'],
        Decimal('0.6500'),
    )


def build_recommendations(run: TrustCalibrationRun, snapshots: list[AutomationFeedbackSnapshot]) -> list[TrustCalibrationRecommendation]:
    recommendations: list[TrustCalibrationRecommendation] = []
    for snapshot in snapshots:
        rec_type, recommended_tier, rationale, reason_codes, confidence = _recommend_for_snapshot(snapshot)
        recommendations.append(
            TrustCalibrationRecommendation.objects.create(
                run=run,
                snapshot=snapshot,
                recommendation_type=rec_type,
                action_type=snapshot.action_type,
                current_trust_tier=snapshot.current_trust_tier,
                recommended_trust_tier=recommended_tier,
                confidence=confidence,
                rationale=rationale,
                reason_codes=reason_codes,
                supporting_metrics=snapshot.metrics,
                metadata={
                    'source_type': snapshot.source_type,
                    'runbook_template_slug': snapshot.runbook_template_slug,
                    'profile_slug': snapshot.profile_slug,
                },
            )
        )
    return recommendations
