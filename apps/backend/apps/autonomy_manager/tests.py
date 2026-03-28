from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequestStatus
from apps.approval_center.services import apply_decision
from apps.automation_policy.models import AutomationPolicyProfile, AutomationPolicyRule, AutomationTrustTier
from apps.autonomy_manager.models import AutonomyRecommendationCode, AutonomyTransitionStatus
from apps.policy_rollout.models import PolicyRolloutRecommendation, PolicyRolloutRecommendationCode, PolicyRolloutRun
from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidate
from apps.trust_calibration.models import (
    AutomationFeedbackSnapshot,
    TrustCalibrationRecommendation,
    TrustCalibrationRecommendationType,
    TrustCalibrationRun,
    TrustCalibrationRunStatus,
)


class AutonomyManagerTests(TestCase):
    def setUp(self):
        self.profile = AutomationPolicyProfile.objects.create(slug='autonomy_profile', name='Autonomy profile', is_active=True, is_default=True)
        self.rule = AutomationPolicyRule.objects.create(
            profile=self.profile,
            action_type='runbook_step_execute',
            trust_tier=AutomationTrustTier.MANUAL_ONLY,
            rationale='baseline',
        )

    def _create_trust_recommendations_same_run(self, action_types: list[str], recommendation_type: str):
        run = TrustCalibrationRun.objects.create(status=TrustCalibrationRunStatus.READY, summary='autonomy test')
        for action_type in action_types:
            snapshot = AutomationFeedbackSnapshot.objects.create(
                run=run,
                action_type=action_type,
                current_trust_tier=AutomationTrustTier.MANUAL_ONLY,
                metrics={'auto_execution_success_rate': '0.9200'},
            )
            TrustCalibrationRecommendation.objects.create(
                run=run,
                snapshot=snapshot,
                recommendation_type=recommendation_type,
                action_type=action_type,
                current_trust_tier=AutomationTrustTier.MANUAL_ONLY,
                recommended_trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
                confidence='0.9100',
                rationale='test recommendation',
                reason_codes=['TEST'],
                supporting_metrics={'auto_execution_success_rate': '0.9200'},
            )

    def _create_rollout_rollback_signal(self):
        candidate = PolicyTuningCandidate.objects.create(action_type='runbook_step_execute', status='APPLIED')
        app_log = PolicyTuningApplicationLog.objects.create(candidate=candidate, applied_at=timezone.now())
        rollout = PolicyRolloutRun.objects.create(policy_tuning_candidate=candidate, application_log=app_log)
        PolicyRolloutRecommendation.objects.create(
            run=rollout,
            recommendation=PolicyRolloutRecommendationCode.ROLLBACK_CHANGE,
            rationale='roll back',
        )

    def test_domain_mapping_seeded(self):
        response = self.client.get(reverse('autonomy_manager:domains'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        slugs = {item['slug'] for item in payload}
        self.assertIn('incident_response', slugs)
        self.assertIn('runbook_remediation', slugs)

    def test_recommendation_promote_keep_and_downgrade(self):
        self._create_trust_recommendations_same_run(
            ['runbook_step_execute', 'runbook_checkpoint_continue'],
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
        )

        review = self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json')
        self.assertEqual(review.status_code, 200)
        recs = review.json()['recommendations']
        runbook_rec = next(item for item in recs if item['domain_slug'] == 'runbook_remediation')
        self.assertEqual(runbook_rec['recommendation_code'], AutonomyRecommendationCode.PROMOTE_TO_ASSISTED)

        self._create_rollout_rollback_signal()
        review_after_risk = self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json').json()['recommendations']
        runbook_rec_after_risk = next(item for item in review_after_risk if item['domain_slug'] == 'runbook_remediation')
        self.assertEqual(runbook_rec_after_risk['recommendation_code'], AutonomyRecommendationCode.FREEZE_DOMAIN)

    def test_transition_apply_and_rollback(self):
        self._create_trust_recommendations_same_run(
            ['runbook_step_execute', 'runbook_checkpoint_continue'],
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
        )

        review = self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json').json()
        transition = next((item['transition'] for item in review['recommendations'] if item['domain_slug'] == 'runbook_remediation' and item['transition']), None)
        self.assertIsNotNone(transition)

        apply_response = self.client.post(reverse('autonomy_manager:transition-apply', args=[transition['id']]), data={}, content_type='application/json')
        self.assertEqual(apply_response.status_code, 200)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.trust_tier, AutomationTrustTier.APPROVAL_REQUIRED)

        rollback_response = self.client.post(reverse('autonomy_manager:transition-rollback', args=[transition['id']]), data={}, content_type='application/json')
        self.assertEqual(rollback_response.status_code, 200)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.trust_tier, AutomationTrustTier.MANUAL_ONLY)

    def test_transition_requires_approval_for_high_impact(self):
        self._create_trust_recommendations_same_run(
            ['runbook_step_execute', 'runbook_checkpoint_continue'],
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
        )
        # Move domain once to ASSISTED.
        first_review = self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json').json()
        first_transition = next(item['transition'] for item in first_review['recommendations'] if item['domain_slug'] == 'runbook_remediation' and item['transition'])
        self.client.post(reverse('autonomy_manager:transition-apply', args=[first_transition['id']]), data={}, content_type='application/json')

        # New review should now propose ASSISTED -> SUPERVISED_AUTOPILOT requiring approval.
        self._create_trust_recommendations_same_run(
            ['runbook_step_execute', 'runbook_checkpoint_continue'],
            TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
        )
        second_review = self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json').json()
        pending_transition = next((item['transition'] for item in second_review['recommendations'] if item['domain_slug'] == 'runbook_remediation' and item['transition'] and item['transition']['status'] == AutonomyTransitionStatus.PENDING_APPROVAL), None)
        self.assertIsNotNone(pending_transition)

        blocked = self.client.post(reverse('autonomy_manager:transition-apply', args=[pending_transition['id']]), data={}, content_type='application/json')
        self.assertEqual(blocked.status_code, 400)

        from apps.autonomy_manager.models import AutonomyStageTransition

        transition_obj = AutonomyStageTransition.objects.get(pk=pending_transition['id'])
        apply_decision(approval=transition_obj.approval_request, decision='APPROVE', rationale='approved for test')
        transition_obj.refresh_from_db()
        self.assertEqual(transition_obj.approval_request.status, ApprovalRequestStatus.APPROVED)

        applied = self.client.post(reverse('autonomy_manager:transition-apply', args=[pending_transition['id']]), data={}, content_type='application/json')
        self.assertEqual(applied.status_code, 200)

    def test_core_endpoints(self):
        self.client.post(reverse('autonomy_manager:run-review'), data={}, content_type='application/json')
        urls = [
            reverse('autonomy_manager:domains'),
            reverse('autonomy_manager:states'),
            reverse('autonomy_manager:recommendations'),
            reverse('autonomy_manager:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
