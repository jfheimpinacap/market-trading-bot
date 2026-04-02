from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile, ReadinessStatus
from apps.runtime_governor.models import (
    GlobalModeEnforcementDecision,
    GlobalModeEnforcementRun,
    GlobalModeModuleImpact,
    GlobalOperatingModeDecision,
    RuntimeMode,
    RuntimeSetBy,
    RuntimeTransitionLog,
)
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state, set_runtime_mode
from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus, AutonomousSessionHealthSnapshot, AutonomousSessionHealthStatus
from apps.mission_control.services.session_timing.timing import evaluate_session_timing
from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
    PortfolioExposureDecisionType,
)
from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionDecisionType
from apps.autonomous_trader.services.execution_intake.decision import decide_intake_candidate
from apps.markets.models import Market, Provider
from apps.safety_guard.services.kill_switch import enable_kill_switch


class RuntimeGovernorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.profile = ReadinessProfile.objects.create(name='Balanced', slug='balanced', profile_type='balanced')
        self.provider = Provider.objects.create(name='Test Provider', slug='test-provider')

    def _set_readiness(self, status: str):
        ReadinessAssessmentRun.objects.create(readiness_profile=self.profile, status=status, summary='test run')

    def test_manual_mode_change(self):
        result = set_runtime_mode(requested_mode=RuntimeMode.PAPER_ASSIST, set_by=RuntimeSetBy.OPERATOR, rationale='manual step-down')
        self.assertTrue(result['changed'])
        state = get_runtime_state()
        self.assertEqual(state.current_mode, RuntimeMode.PAPER_ASSIST)

    def test_invalid_transition_due_to_readiness(self):
        self._set_readiness(ReadinessStatus.NOT_READY)
        response = self.client.post(reverse('runtime_governor:set_mode'), {'mode': RuntimeMode.PAPER_AUTO, 'set_by': 'operator'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('blocked_reasons', response.json())

    def test_degrade_to_observe_only_when_kill_switch_enabled(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_AUTO, set_by=RuntimeSetBy.OPERATOR, rationale='prepare auto')
        enable_kill_switch()
        status_response = self.client.get(reverse('runtime_governor:status'))
        self.assertEqual(status_response.status_code, 200)
        payload = status_response.json()
        self.assertEqual(payload['state']['current_mode'], RuntimeMode.OBSERVE_ONLY)
        self.assertEqual(payload['state']['status'], 'STOPPED')

    def test_capabilities_by_mode(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_SEMI_AUTO, set_by=RuntimeSetBy.OPERATOR, rationale='semi')
        caps = get_capabilities_for_current_mode()
        self.assertTrue(caps['allow_auto_execution'])
        self.assertFalse(caps['require_operator_for_all_trades'])

    def test_endpoints(self):
        status_response = self.client.get(reverse('runtime_governor:status'))
        modes_response = self.client.get(reverse('runtime_governor:modes'))
        transitions_response = self.client.get(reverse('runtime_governor:transitions'))
        capabilities_response = self.client.get(reverse('runtime_governor:capabilities'))

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(modes_response.status_code, 200)
        self.assertEqual(transitions_response.status_code, 200)
        self.assertEqual(capabilities_response.status_code, 200)

    def test_transition_log_created(self):
        set_runtime_mode(requested_mode=RuntimeMode.PAPER_ASSIST, set_by=RuntimeSetBy.OPERATOR, rationale='assist mode')
        self.assertGreaterEqual(RuntimeTransitionLog.objects.count(), 1)

    def _seed_exposure_decision(self, decision_type: str):
        run = PortfolioExposureCoordinationRun.objects.create()
        cluster = PortfolioExposureClusterSnapshot.objects.create(linked_run=run, cluster_label='cluster')
        return PortfolioExposureDecision.objects.create(linked_cluster_snapshot=cluster, decision_type=decision_type, decision_summary='test')

    def test_operating_mode_review_normal_context_keeps_balanced(self):
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        latest = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.target_mode, 'BALANCED')

    def test_operating_mode_review_quiet_market_switches_monitor_only(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        from apps.mission_control.models import AutonomousSessionTimingSnapshot, AutonomousTimingDecision, AutonomousTimingDecisionType

        timing_snapshot = AutonomousSessionTimingSnapshot.objects.create(linked_session=session, timing_status='MONITOR_ONLY_WINDOW')
        AutonomousTimingDecision.objects.create(
            linked_session=session,
            linked_timing_snapshot=timing_snapshot,
            decision_type=AutonomousTimingDecisionType.MONITOR_ONLY_NEXT,
            decision_summary='quiet',
        )
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        latest = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()
        self.assertEqual(latest.target_mode, 'MONITOR_ONLY')

    def test_operating_mode_review_repeated_losses_switches_recovery(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        AutonomousSessionHealthSnapshot.objects.create(linked_session=session, session_health_status=AutonomousSessionHealthStatus.CAUTION, recent_loss_count=3)
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        latest = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()
        self.assertEqual(latest.target_mode, 'RECOVERY_MODE')

    def test_operating_mode_review_pressure_switches_throttled(self):
        self._seed_exposure_decision(PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES)
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        latest = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()
        self.assertEqual(latest.target_mode, 'THROTTLED')

    def test_operating_mode_review_hard_block_switches_blocked(self):
        enable_kill_switch()
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        latest = GlobalOperatingModeDecision.objects.order_by('-created_at_decision', '-id').first()
        self.assertEqual(latest.target_mode, 'BLOCKED')

    def test_operating_mode_summary_endpoint(self):
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:operating_mode_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('active_mode', payload)


    def test_mode_enforcement_balanced_keeps_modules_unchanged(self):
        response = self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        latest_run = GlobalModeEnforcementRun.objects.order_by('-started_at', '-id').first()
        self.assertIsNotNone(latest_run)
        self.assertEqual(latest_run.current_mode, 'BALANCED')
        self.assertEqual(latest_run.affected_module_count, 0)

    def test_mode_enforcement_caution_reduces_cadence_and_admission(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        from apps.mission_control.models import AutonomousSessionTimingSnapshot, AutonomousTimingDecision, AutonomousTimingDecisionType

        timing_snapshot = AutonomousSessionTimingSnapshot.objects.create(linked_session=session, timing_status='WAIT_WINDOW')
        AutonomousTimingDecision.objects.create(
            linked_session=session,
            linked_timing_snapshot=timing_snapshot,
            decision_type=AutonomousTimingDecisionType.WAIT_SHORT,
            decision_summary='caution signal',
        )
        self._seed_exposure_decision(PortfolioExposureDecisionType.PARK_WEAKER_SESSION)
        response = self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.assertEqual(response.status_code, 200)
        response2 = self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response2.status_code, 200)
        decisions = GlobalModeEnforcementDecision.objects.filter(linked_enforcement_run__current_mode='CAUTION')
        self.assertTrue(decisions.filter(module_name='timing_policy', decision_type='REDUCE_CADENCE').exists())
        self.assertTrue(decisions.filter(module_name='session_admission', decision_type='REDUCE_ADMISSION_CAPACITY').exists())

    def test_mode_enforcement_monitor_only_blocks_execution(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        from apps.mission_control.models import AutonomousSessionTimingSnapshot, AutonomousTimingDecision, AutonomousTimingDecisionType

        timing_snapshot = AutonomousSessionTimingSnapshot.objects.create(linked_session=session, timing_status='MONITOR_ONLY_WINDOW')
        AutonomousTimingDecision.objects.create(
            linked_session=session,
            linked_timing_snapshot=timing_snapshot,
            decision_type=AutonomousTimingDecisionType.MONITOR_ONLY_NEXT,
            decision_summary='quiet',
        )
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        self.assertTrue(GlobalModeModuleImpact.objects.filter(module_name='execution_intake', impact_status='BLOCKED').exists())

    def test_mode_enforcement_recovery_and_throttled_harden_exposure(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        AutonomousSessionHealthSnapshot.objects.create(linked_session=session, session_health_status=AutonomousSessionHealthStatus.CAUTION, recent_loss_count=3)
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        self.assertTrue(GlobalModeEnforcementDecision.objects.filter(module_name='exposure_coordination', decision_type='THROTTLE_EXPOSURE').exists())

    def test_mode_enforcement_blocked_blocks_new_activity(self):
        enable_kill_switch()
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        latest = GlobalModeEnforcementRun.objects.order_by('-started_at', '-id').first()
        self.assertEqual(latest.current_mode, 'BLOCKED')
        self.assertGreaterEqual(latest.blocked_module_count, 1)

    def test_mode_enforcement_summary_endpoint(self):
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:mode_enforcement_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('current_mode', payload)

    def test_mode_enforcement_propagates_to_timing_policy(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        self._seed_exposure_decision(PortfolioExposureDecisionType.PARK_WEAKER_SESSION)
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')

        timing_review = evaluate_session_timing(session=session)
        self.assertEqual(timing_review.decision.decision_type, 'WAIT_SHORT')
        self.assertIn('global_mode_enforcement_reduce_cadence', timing_review.decision.reason_codes)

    def test_mode_enforcement_propagates_to_execution_intake(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        from apps.mission_control.models import AutonomousSessionTimingSnapshot, AutonomousTimingDecision, AutonomousTimingDecisionType

        timing_snapshot = AutonomousSessionTimingSnapshot.objects.create(linked_session=session, timing_status='MONITOR_ONLY_WINDOW')
        AutonomousTimingDecision.objects.create(
            linked_session=session,
            linked_timing_snapshot=timing_snapshot,
            decision_type=AutonomousTimingDecisionType.MONITOR_ONLY_NEXT,
            decision_summary='quiet',
        )
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')

        market = Market.objects.create(
            provider=self.provider,
            provider_market_id='mode-enforcement-test',
            title='Mode enforcement intake test',
            status='open',
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create()
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            intake_status='READY_FOR_AUTONOMOUS_EXECUTION',
            approval_status='AUTO_APPROVED',
            readiness_confidence='0.9000',
        )
        decision = decide_intake_candidate(candidate=candidate)
        self.assertEqual(decision.decision_type, AutonomousExecutionDecisionType.BLOCK)
        self.assertIn('GLOBAL_MODE_ENFORCEMENT_BLOCKED', decision.reason_codes)
