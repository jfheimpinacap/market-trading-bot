from django.test import TestCase
from django.urls import reverse

from apps.automation_policy.models import AutomationActionLog, AutomationDecision, AutomationTrustTier
from apps.automation_policy.services import apply_profile, evaluate_action
from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, OperatingEnvelope
from apps.incident_commander.models import DegradedModeState, DegradedSystemState
from apps.runtime_governor.models import RuntimeMode, RuntimeModeState, RuntimeStateStatus
from apps.safety_guard.models import SafetyPolicyConfig, SafetyStatus


class AutomationPolicyTests(TestCase):
    def test_safe_action_evaluates_allowed_under_supervised_profile(self):
        apply_profile(profile_slug='supervised_autopilot')
        result = evaluate_action(action_type='run_incident_detection', source_context_type='incident')
        self.assertEqual(result.decision.effective_trust_tier, AutomationTrustTier.SAFE_AUTOMATION)
        self.assertTrue(result.can_auto_execute)

    def test_live_execution_is_blocked(self):
        result = evaluate_action(action_type='live_execution')
        self.assertEqual(result.decision.effective_trust_tier, AutomationTrustTier.AUTO_BLOCKED)
        self.assertTrue(result.blocked)

    def test_sensitive_action_requires_approval(self):
        result = evaluate_action(action_type='rollback_rollout')
        self.assertEqual(result.decision.effective_trust_tier, AutomationTrustTier.APPROVAL_REQUIRED)
        self.assertTrue(result.approval_required)

    def test_runtime_safety_and_certification_can_downgrade(self):
        RuntimeModeState.objects.create(current_mode=RuntimeMode.PAPER_AUTO, status=RuntimeStateStatus.DEGRADED, set_by='system', rationale='test')
        SafetyPolicyConfig.objects.create(status=SafetyStatus.HARD_STOP, status_message='hard stop')
        CertificationRun.objects.create(
            decision_mode='RECOMMENDATION_ONLY',
            certification_level=CertificationLevel.REMEDIATION_REQUIRED,
            recommendation_code=CertificationRecommendationCode.REQUIRE_REMEDIATION,
            confidence=0.2,
            rationale='needs remediation',
            evidence_snapshot=CertificationEvidenceSnapshot.objects.create(),
            operating_envelope=OperatingEnvelope.objects.create(),
        )
        DegradedModeState.objects.create(state=DegradedSystemState.DEFENSIVE_ONLY)

        result = evaluate_action(action_type='run_certification_review')
        self.assertEqual(result.decision.effective_trust_tier, AutomationTrustTier.MANUAL_ONLY)

    def test_evaluate_endpoint_and_action_log(self):
        apply_profile(profile_slug='supervised_autopilot')
        response = self.client.post(
            reverse('automation_policy:evaluate'),
            data={'action_type': 'run_incident_detection', 'execute': True},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('decision', payload)
        self.assertIn('action_log', payload)
        self.assertGreaterEqual(AutomationDecision.objects.count(), 1)
        self.assertGreaterEqual(AutomationActionLog.objects.count(), 1)

    def test_core_endpoints(self):
        urls = [
            reverse('automation_policy:profiles'),
            reverse('automation_policy:current'),
            reverse('automation_policy:decisions'),
            reverse('automation_policy:action-logs'),
            reverse('automation_policy:summary'),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
