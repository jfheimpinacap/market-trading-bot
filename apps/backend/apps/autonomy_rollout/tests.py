from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.approval_center.models import ApprovalRequest, ApprovalRequestStatus
from apps.automation_policy.models import AutomationActionExecutionStatus, AutomationActionLog, AutomationDecision, AutomationDecisionOutcome, AutomationPolicyProfile, AutomationPolicyRule, AutomationTrustTier
from apps.autonomy_manager.models import AutonomyDomain, AutonomyDomainStatus, AutonomyStage, AutonomyStageRecommendation, AutonomyStageState, AutonomyStageTransition, AutonomyTransitionStatus
from apps.autonomy_rollout.models import AutonomyRolloutRecommendationCode
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus


class AutonomyRolloutTests(TestCase):
    def setUp(self):
        self.profile = AutomationPolicyProfile.objects.create(slug='autonomy_rollout_profile', name='Autonomy rollout profile', is_active=True, is_default=True)
        self.rule = AutomationPolicyRule.objects.create(
            profile=self.profile,
            action_type='pause_rollout',
            source_context_type='',
            trust_tier=AutomationTrustTier.APPROVAL_REQUIRED,
            conditions={'paper_only': True},
            rationale='baseline',
        )

        self.domain = AutonomyDomain.objects.create(slug='rollout-domain', name='Rollout Domain', owner_app='autonomy_manager', action_types=['pause_rollout'], source_apps=['automation_policy'])
        self.state = AutonomyStageState.objects.create(domain=self.domain, current_stage=AutonomyStage.ASSISTED, effective_stage=AutonomyStage.ASSISTED, status=AutonomyDomainStatus.ACTIVE)
        self.recommendation = AutonomyStageRecommendation.objects.create(
            domain=self.domain,
            state=self.state,
            recommendation_code='PROMOTE_TO_SUPERVISED_AUTOPILOT',
            current_stage=AutonomyStage.ASSISTED,
            proposed_stage=AutonomyStage.SUPERVISED_AUTOPILOT,
            rationale='promote with caution',
            reason_codes=['GOOD_SIGNAL'],
            confidence='0.9000',
        )
        self.transition = AutonomyStageTransition.objects.create(
            domain=self.domain,
            state=self.state,
            recommendation=self.recommendation,
            status=AutonomyTransitionStatus.APPLIED,
            previous_stage=AutonomyStage.ASSISTED,
            requested_stage=AutonomyStage.SUPERVISED_AUTOPILOT,
            applied_stage=AutonomyStage.SUPERVISED_AUTOPILOT,
            applied_by='test',
            applied_at=timezone.now(),
        )

    def _create_post_change_signals(self, *, bad: bool = False):
        for i in range(6):
            ApprovalRequest.objects.create(
                source_type='other',
                source_object_id=f'approval-{i}-{bad}',
                title='Autonomy action approval',
                summary='test',
                status=ApprovalRequestStatus.REJECTED if bad else ApprovalRequestStatus.APPROVED,
                requested_at=timezone.now(),
                metadata={'action_type': 'pause_rollout'},
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
                title='Auto failure after transition',
                summary='failure after autonomy transition apply',
                severity=IncidentSeverity.HIGH,
                status=IncidentStatus.OPEN,
                source_app='automation_policy',
                related_object_type='automation_decision',
                related_object_id=str(decision.id),
                first_seen_at=timezone.now(),
                last_seen_at=timezone.now(),
            )

    def test_start_rollout_from_applied_transition_and_baseline(self):
        response = self.client.post(reverse('autonomy_rollout:start'), data={'autonomy_stage_transition_id': self.transition.id}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['rollout_status'], 'OBSERVING')
        self.assertTrue(payload['baseline_snapshot'])

    def test_require_more_data_when_sample_is_ambiguous(self):
        start = self.client.post(reverse('autonomy_rollout:start'), data={'autonomy_stage_transition_id': self.transition.id}, content_type='application/json').json()
        evaluate = self.client.post(reverse('autonomy_rollout:evaluate', args=[start['id']]), data={}, content_type='application/json')
        self.assertEqual(evaluate.status_code, 200)
        self.assertEqual(evaluate.json()['recommendation'], AutonomyRolloutRecommendationCode.REQUIRE_MORE_DATA)

    def test_rollback_recommendation_when_metrics_degrade(self):
        start = self.client.post(reverse('autonomy_rollout:start'), data={'autonomy_stage_transition_id': self.transition.id}, content_type='application/json').json()
        self._create_post_change_signals(bad=True)
        evaluate = self.client.post(reverse('autonomy_rollout:evaluate', args=[start['id']]), data={}, content_type='application/json')
        self.assertEqual(evaluate.status_code, 200)
        self.assertEqual(evaluate.json()['recommendation'], AutonomyRolloutRecommendationCode.ROLLBACK_STAGE)

    def test_manual_rollback_apply(self):
        start = self.client.post(reverse('autonomy_rollout:start'), data={'autonomy_stage_transition_id': self.transition.id}, content_type='application/json').json()
        rollback = self.client.post(
            reverse('autonomy_rollout:rollback', args=[start['id']]),
            data={'reason': 'Operator requested rollback due to incident spike.', 'require_approval': True},
            content_type='application/json',
        )
        self.assertEqual(rollback.status_code, 200)
        self.transition.refresh_from_db()
        self.assertEqual(self.transition.status, AutonomyTransitionStatus.ROLLED_BACK)

    def test_core_endpoints(self):
        start = self.client.post(reverse('autonomy_rollout:start'), data={'autonomy_stage_transition_id': self.transition.id}, content_type='application/json').json()
        urls = [
            reverse('autonomy_rollout:runs'),
            reverse('autonomy_rollout:run-detail', args=[start['id']]),
            reverse('autonomy_rollout:summary'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        rollback = self.client.post(reverse('autonomy_rollout:rollback', args=[start['id']]), data={'reason': 'manual'}, content_type='application/json')
        self.assertEqual(rollback.status_code, 200)
        self.assertTrue(rollback.json()['rollback_outcome']['transition_id'])
