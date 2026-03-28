from django.test import TestCase
from django.urls import reverse

from apps.automation_policy.models import AutomationPolicyProfile, AutomationPolicyRule, AutomationTrustTier
from apps.policy_tuning.models import PolicyTuningApplicationLog, PolicyTuningCandidateStatus
from apps.trust_calibration.models import (
    AutomationFeedbackSnapshot,
    TrustCalibrationRecommendation,
    TrustCalibrationRecommendationType,
    TrustCalibrationRun,
    TrustCalibrationRunStatus,
)


class PolicyTuningTests(TestCase):
    def setUp(self):
        self.profile = AutomationPolicyProfile.objects.create(
            slug='test_policy_tuning_profile',
            name='Test policy tuning profile',
            is_active=True,
            is_default=True,
        )
        self.rule = AutomationPolicyRule.objects.create(
            profile=self.profile,
            action_type='pause_rollout',
            source_context_type='',
            trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            conditions={'paper_only': True},
            rationale='Baseline rule',
        )
        run = TrustCalibrationRun.objects.create(status=TrustCalibrationRunStatus.READY, summary='test')
        snapshot = AutomationFeedbackSnapshot.objects.create(
            run=run,
            action_type='pause_rollout',
            current_trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            metrics={'approval_rate': '0.9500'},
        )
        self.recommendation = TrustCalibrationRecommendation.objects.create(
            run=run,
            snapshot=snapshot,
            recommendation_type=TrustCalibrationRecommendationType.PROMOTE_TO_SAFE_AUTOMATION,
            action_type='pause_rollout',
            current_trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            recommended_trust_tier=AutomationTrustTier.SAFE_AUTOMATION,
            confidence='0.9100',
            rationale='High approval quality and no incidents.',
            reason_codes=['HIGH_APPROVAL_RATE'],
            supporting_metrics={'approval_rate': '0.9500'},
            metadata={'trace_root': {'root_type': 'trust_calibration_run', 'root_id': '1'}},
        )

    def test_create_candidate_from_recommendation(self):
        response = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['action_type'], 'pause_rollout')
        self.assertEqual(payload['current_trust_tier'], AutomationTrustTier.APPROVAL_REQUIRED)
        self.assertEqual(payload['proposed_trust_tier'], AutomationTrustTier.SAFE_AUTOMATION)
        self.assertEqual(payload['status'], PolicyTuningCandidateStatus.PENDING_APPROVAL)

    def test_diff_current_to_proposed(self):
        create = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        )
        candidate_id = create.json()['id']
        detail = self.client.get(reverse('policy_tuning:candidate-detail', args=[candidate_id]))
        self.assertEqual(detail.status_code, 200)
        candidate = detail.json()
        self.assertEqual(candidate['change_set']['diff']['trust_tier']['current'], AutomationTrustTier.APPROVAL_REQUIRED)
        self.assertEqual(candidate['change_set']['diff']['trust_tier']['proposed'], AutomationTrustTier.SAFE_AUTOMATION)

    def test_review_approve_and_reject(self):
        create = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        )
        candidate_id = create.json()['id']

        approve = self.client.post(
            reverse('policy_tuning:candidate-review', args=[candidate_id]),
            data={'decision': 'APPROVE', 'reviewer_note': 'Looks good.'},
            content_type='application/json',
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()['status'], PolicyTuningCandidateStatus.APPROVED)

        candidate = self.client.get(reverse('policy_tuning:candidate-detail', args=[candidate_id])).json()
        self.assertEqual(candidate['approval_request'], create.json()['approval_request'])

        reject = self.client.post(
            reverse('policy_tuning:candidate-review', args=[candidate_id]),
            data={'decision': 'REJECT', 'reviewer_note': 'Stopping for now.'},
            content_type='application/json',
        )
        self.assertEqual(reject.status_code, 200)
        self.assertEqual(reject.json()['status'], PolicyTuningCandidateStatus.REJECTED)

    def test_apply_to_automation_policy_and_persist_log(self):
        create = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        )
        candidate_id = create.json()['id']
        self.client.post(
            reverse('policy_tuning:candidate-review', args=[candidate_id]),
            data={'decision': 'APPROVE'},
            content_type='application/json',
        )

        apply_response = self.client.post(
            reverse('policy_tuning:candidate-apply', args=[candidate_id]),
            data={'note': 'Manual operator apply.'},
            content_type='application/json',
        )
        self.assertEqual(apply_response.status_code, 200)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.trust_tier, AutomationTrustTier.SAFE_AUTOMATION)

        self.assertTrue(PolicyTuningApplicationLog.objects.filter(candidate_id=candidate_id).exists())
        candidate_detail = self.client.get(reverse('policy_tuning:candidate-detail', args=[candidate_id])).json()
        self.assertEqual(candidate_detail['status'], PolicyTuningCandidateStatus.APPLIED)

    def test_core_endpoints(self):
        created = self.client.post(
            reverse('policy_tuning:create-candidate'),
            data={'recommendation_id': self.recommendation.id},
            content_type='application/json',
        ).json()
        candidate_id = created['id']

        urls = [
            reverse('policy_tuning:candidates'),
            reverse('policy_tuning:candidate-detail', args=[candidate_id]),
            reverse('policy_tuning:application-logs'),
            reverse('policy_tuning:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
