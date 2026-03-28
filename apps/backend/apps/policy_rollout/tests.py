from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog, AutomationDecision, AutomationDecisionOutcome, AutomationPolicyProfile, AutomationPolicyRule, AutomationTrustTier
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.policy_rollout.models import PolicyRolloutRecommendationCode
from apps.policy_tuning.models import PolicyTuningCandidateStatus
from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRecommendationType, TrustCalibrationRun, TrustCalibrationRunStatus


class PolicyRolloutTests(TestCase):
    def setUp(self):
        self.profile = AutomationPolicyProfile.objects.create(slug='rollout_profile', name='Rollout profile', is_active=True, is_default=True)
        self.rule = AutomationPolicyRule.objects.create(
            profile=self.profile,
            action_type='pause_rollout',
            source_context_type='',
            trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            conditions={'paper_only': True},
            rationale='baseline',
        )
        run = TrustCalibrationRun.objects.create(status=TrustCalibrationRunStatus.READY, summary='ready')
        snapshot = AutomationFeedbackSnapshot.objects.create(run=run, action_type='pause_rollout', current_trust_tier=AutomationTrustTier.APPROVAL_REQUIRED)
        self.recommendation = TrustCalibrationRecommendation.objects.create(
            run=run,
            snapshot=snapshot,
            recommendation_type=TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
            action_type='pause_rollout',
            current_trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            recommended_trust_tier=AutomationTrustTier.SAFE_AUTOMATION,
            confidence='0.9100',
            rationale='promote',
            reason_codes=['HIGH_APPROVAL_RATE'],
            supporting_metrics={},
            metadata={},
        )

        self.candidate = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        ).json()
        self.client.post(reverse('policy_tuning:candidate-review', args=[self.candidate['id']]), data={'decision': 'APPROVE'}, content_type='application/json')
        self.apply_payload = self.client.post(reverse('policy_tuning:candidate-apply', args=[self.candidate['id']]), data={'note': 'apply'}, content_type='application/json').json()

    def _create_post_change_signals(self, *, bad: bool = False):
        for _ in range(6):
            ApprovalRequest.objects.create(
                source_type='other',
                source_object_id=f'approval-{_}-{bad}',
                title='Policy action approval',
                summary='test',
                status=ApprovalRequestStatus.REJECTED if bad else ApprovalRequestStatus.APPROVED,
                requested_at=self.apply_payload['application_log']['applied_at'],
                metadata={'action_type': 'pause_rollout', 'retry_count': 1 if bad else 0},
            )
        decision = AutomationDecision.objects.create(
            profile=self.profile,
            rule=self.rule,
            action_type='pause_rollout',
            source_context_type='',
            trust_tier=self.rule.trust_tier,
            effective_trust_tier=self.rule.trust_tier,
            outcome=AutomationDecisionOutcome.BLOCKED if bad else AutomationDecisionOutcome.ALLOWED,
            metadata={},
        )
        AutomationActionLog.objects.create(
            decision=decision,
            action_name='pause_rollout',
            execution_status=AutomationActionExecutionStatus.FAILED if bad else AutomationActionExecutionStatus.EXECUTED,
            result_summary='post-change',
        )
        if bad:
            IncidentRecord.objects.create(
                incident_type='execution_anomaly',
                title='Auto failure after tuning',
                summary='failure after policy tuning apply',
                severity=IncidentSeverity.HIGH,
                status=IncidentStatus.OPEN,
                source_app='policy_rollout',
                related_object_type='automation_decision',
                related_object_id=str(decision.id),
                first_seen_at=timezone.now(),
                last_seen_at=timezone.now(),
            )

    def test_start_rollout_from_applied_candidate_and_baseline(self):
        response = self.client.post(reverse('policy_rollout:start'), data={'policy_tuning_candidate_id': self.candidate['id']}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['rollout_status'], 'OBSERVING')
        self.assertTrue(payload['baseline_snapshot'])

    def test_require_more_data_when_sample_is_ambiguous(self):
        start = self.client.post(reverse('policy_rollout:start'), data={'policy_tuning_candidate_id': self.candidate['id']}, content_type='application/json').json()
        evaluate = self.client.post(reverse('policy_rollout:evaluate', args=[start['id']]), data={}, content_type='application/json')
        self.assertEqual(evaluate.status_code, 200)
        self.assertEqual(evaluate.json()['recommendation'], PolicyRolloutRecommendationCode.REQUIRE_MORE_DATA)

    def test_rollback_recommendation_when_metrics_degrade(self):
        start = self.client.post(reverse('policy_rollout:start'), data={'policy_tuning_candidate_id': self.candidate['id']}, content_type='application/json').json()
        self._create_post_change_signals(bad=True)
        evaluate = self.client.post(reverse('policy_rollout:evaluate', args=[start['id']]), data={}, content_type='application/json')
        self.assertEqual(evaluate.status_code, 200)
        self.assertEqual(evaluate.json()['recommendation'], PolicyRolloutRecommendationCode.ROLLBACK_CHANGE)

    def test_manual_rollback_apply(self):
        start = self.client.post(reverse('policy_rollout:start'), data={'policy_tuning_candidate_id': self.candidate['id']}, content_type='application/json').json()
        rollback = self.client.post(
            reverse('policy_rollout:rollback', args=[start['id']]),
            data={'reason': 'Operator requested rollback due to incident spike.', 'require_approval': True},
            content_type='application/json',
        )
        self.assertEqual(rollback.status_code, 200)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.trust_tier, AutomationTrustTier.APPROVAL_REQUIRED)

    def test_core_endpoints(self):
        start = self.client.post(reverse('policy_rollout:start'), data={'policy_tuning_candidate_id': self.candidate['id']}, content_type='application/json').json()
        urls = [
            reverse('policy_rollout:runs'),
            reverse('policy_rollout:run-detail', args=[start['id']]),
            reverse('policy_rollout:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        rollback = self.client.post(reverse('policy_rollout:rollback', args=[start['id']]), data={'reason': 'manual'}, content_type='application/json')
        self.assertEqual(rollback.status_code, 200)
        candidate_status = rollback.json()['run']['policy_tuning_candidate']
        self.assertTrue(candidate_status)

        candidate = self.client.get(reverse('policy_tuning:candidate-detail', args=[self.candidate['id']])).json()
        self.assertEqual(candidate['status'], PolicyTuningCandidateStatus.SUPERSEDED)
