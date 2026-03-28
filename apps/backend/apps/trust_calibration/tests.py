from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus, ApprovalSourceType
from apps.automation_policy.models import (
    AutomationPolicyProfile,
    AutomationActionExecutionStatus,
    AutomationActionLog,
    AutomationDecision,
    AutomationDecisionOutcome,
    AutomationPolicyRule,
    AutomationTrustTier,
)
from apps.trust_calibration.models import TrustCalibrationRecommendationType
from apps.trust_calibration.services.recommendation import build_recommendations


class TrustCalibrationTests(TestCase):
    def setUp(self):
        self.profile = AutomationPolicyProfile.objects.create(
            slug='test_profile',
            name='Test profile',
            is_active=True,
            recommendation_mode=False,
            allow_runbook_auto_advance=True,
        )

    def _create_approval(self, action_type: str, status: str):
        return ApprovalRequest.objects.create(
            source_type=ApprovalSourceType.RUNBOOK_CHECKPOINT,
            source_object_id=f'{action_type}-{status}-{timezone.now().timestamp()}',
            title=f'{action_type} decision',
            status=status,
            requested_at=timezone.now(),
            metadata={'action_type': action_type, 'policy_profile_slug': self.profile.slug, 'runbook_template_slug': 'incident_recovery'},
        )

    def _create_decision_and_log(self, action_type: str, execution_status: str):
        decision = AutomationDecision.objects.create(
            profile=self.profile,
            action_type=action_type,
            source_context_type='runbook',
            trust_tier=AutomationTrustTier.SAFE_AUTOMATION,
            effective_trust_tier=AutomationTrustTier.SAFE_AUTOMATION,
            outcome=AutomationDecisionOutcome.ALLOWED,
            metadata={'runbook_template_slug': 'incident_recovery', 'source_type': ApprovalSourceType.RUNBOOK_CHECKPOINT},
        )
        AutomationActionLog.objects.create(
            decision=decision,
            action_name=action_type,
            execution_status=execution_status,
            result_summary='test',
        )
        return decision

    def test_feedback_consolidation_basics(self):
        self._create_approval('rebalance_position', ApprovalRequestStatus.APPROVED)
        self._create_approval('rebalance_position', ApprovalRequestStatus.REJECTED)

        run = self.client.post(reverse('trust_calibration:run'), data={'window_days': 30}, content_type='application/json').json()['run']
        feedback = self.client.get(reverse('trust_calibration:feedback'), {'run_id': run['id']}).json()
        self.assertGreaterEqual(len(feedback), 1)

    def test_recommendation_promote_to_safe_automation(self):
        for _ in range(9):
            self._create_approval('clear_cache', ApprovalRequestStatus.APPROVED)
        self._create_approval('clear_cache', ApprovalRequestStatus.REJECTED)
        for _ in range(10):
            self._create_decision_and_log('clear_cache', AutomationActionExecutionStatus.EXECUTED)

        run_payload = self.client.post(reverse('trust_calibration:run'), data={'window_days': 30}, content_type='application/json').json()['run']
        recommendations = self.client.get(reverse('trust_calibration:recommendations'), {'run_id': run_payload['id']}).json()
        promote = [item for item in recommendations if item['action_type'] == 'clear_cache']
        self.assertTrue(promote)
        self.assertEqual(promote[0]['recommendation_type'], TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION)

    def test_recommendation_require_more_data_for_ambiguous_domain(self):
        self._create_approval('restart_connector', ApprovalRequestStatus.APPROVED)
        self._create_approval('restart_connector', ApprovalRequestStatus.REJECTED)

        run_payload = self.client.post(reverse('trust_calibration:run'), data={'window_days': 30}, content_type='application/json').json()['run']
        recommendations = self.client.get(reverse('trust_calibration:recommendations'), {'run_id': run_payload['id']}).json()
        row = [item for item in recommendations if item['action_type'] == 'restart_connector'][0]
        self.assertIn(row['recommendation_type'], [TrustCalibrationRecommendationType.REQUIRE_MORE_DATA, TrustCalibrationRecommendationType.KEEP_APPROVAL_REQUIRED])

    def test_recommendation_downgrade_when_auto_actions_fail(self):
        from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRun

        run = TrustCalibrationRun.objects.create(window_days=30, summary='test run', status='READY')
        snapshot = AutomationFeedbackSnapshot.objects.create(
            run=run,
            action_type='reroute_execution',
            current_trust_tier=AutomationTrustTier.SAFE_AUTOMATION,
            auto_actions_executed=4,
            auto_actions_failed=3,
            incidents_after_auto=2,
            metrics={
                'sample_size': 8,
                'approval_rate': '0.5000',
                'rejection_rate': '0.2000',
                'auto_execution_success_rate': '0.2500',
                'auto_action_followed_by_incident_rate': '0.5000',
                'approval_friction_score': '0.6000',
            },
        )

        recommendations = build_recommendations(run, [snapshot])
        self.assertTrue(recommendations)
        self.assertIn(recommendations[0].recommendation_type, [TrustCalibrationRecommendationType.DOWNGRADE_TO_MANUAL_ONLY, TrustCalibrationRecommendationType.BLOCK_AUTOMATION_FOR_ACTION])

    def test_core_endpoints(self):
        run_response = self.client.post(reverse('trust_calibration:run'), data={'window_days': 15}, content_type='application/json')
        self.assertEqual(run_response.status_code, 201)
        run_id = run_response.json()['run']['id']

        urls = [
            reverse('trust_calibration:runs'),
            reverse('trust_calibration:run-detail', args=[run_id]),
            reverse('trust_calibration:recommendations'),
            reverse('trust_calibration:summary'),
            reverse('trust_calibration:feedback'),
            reverse('trust_calibration:run-report', args=[run_id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
