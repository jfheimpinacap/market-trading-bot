from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from dataclasses import replace
from unittest.mock import patch

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile, ReadinessStatus
from apps.runtime_governor.models import (
    GlobalModeEnforcementDecision,
    GlobalModeEnforcementRun,
    GlobalModeModuleImpact,
    GlobalOperatingModeDecision,
    RuntimeFeedbackApplyDecision,
    RuntimeFeedbackApplyRecord,
    RuntimeFeedbackDecision,
    RuntimeFeedbackRecommendation,
    RuntimeModeStabilityReview,
    RuntimeModeTransitionApplyRecord,
    RuntimeModeTransitionDecision,
    RuntimeMode,
    RuntimeSetBy,
    RuntimeTuningContextSnapshot,
    RuntimeTransitionLog,
)
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state, set_runtime_mode
from apps.runtime_governor.services.tuning_history import create_tuning_context_snapshot
from apps.runtime_governor.services.operating_mode.mode_switch import GLOBAL_MODE_METADATA_KEY
from apps.runtime_governor.tuning_profiles import DEFAULT_CONSERVATIVE_TUNING_PROFILE
from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus, AutonomousSessionHealthSnapshot, AutonomousSessionHealthStatus
from apps.mission_control.models import GovernanceBacklogPressureSnapshot
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

    def test_tuning_profile_summary_endpoint_includes_active_profile(self):
        response = self.client.get(reverse('runtime_governor_v2:tuning_profile_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['profile_name'], DEFAULT_CONSERVATIVE_TUNING_PROFILE.profile_name)
        self.assertIn('summary', payload)

    def test_tuning_profile_summary_endpoint_includes_thresholds_weights_and_guardrails(self):
        response = self.client.get(reverse('runtime_governor_v2:tuning_profile_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload['backlog_thresholds']['high'], DEFAULT_CONSERVATIVE_TUNING_PROFILE.backlog_high_threshold)
        self.assertEqual(payload['backlog_weights']['overdue_weight'], DEFAULT_CONSERVATIVE_TUNING_PROFILE.overdue_weight)
        self.assertEqual(
            payload['feedback_guardrails']['high_backlog_manual_review_bias'],
            DEFAULT_CONSERVATIVE_TUNING_PROFILE.high_backlog_manual_review_bias,
        )
        self.assertEqual(
            payload['operating_mode_guardrails']['critical_backlog_monitor_only_bias'],
            DEFAULT_CONSERVATIVE_TUNING_PROFILE.critical_backlog_monitor_only_bias,
        )
        self.assertEqual(
            payload['stabilization_guardrails']['critical_backlog_relax_dwell_multiplier'],
            DEFAULT_CONSERVATIVE_TUNING_PROFILE.critical_backlog_relax_dwell_multiplier,
        )

    def test_tuning_profile_values_endpoint_returns_profile_values(self):
        response = self.client.get(reverse('runtime_governor_v2:tuning_profile_values'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['profile_name'], DEFAULT_CONSERVATIVE_TUNING_PROFILE.profile_name)
        self.assertEqual(
            payload['profile_values']['critical_backlog_blocks_relax'],
            DEFAULT_CONSERVATIVE_TUNING_PROFILE.critical_backlog_blocks_relax,
        )

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
        self.assertIn('tuning_profile_name', payload)
        self.assertIn('tuning_effective_values', payload)
        self.assertIn('tuning_guardrail_summary', payload)


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
        self.assertIn('tuning_profile_name', payload)
        self.assertIn('tuning_effective_values', payload)
        self.assertIn('tuning_guardrail_summary', payload)

    def test_tuning_context_snapshot_first_is_initial(self):
        snapshot = create_tuning_context_snapshot(
            source_scope='runtime_feedback',
            source_run_id=101,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'abc111',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 1},
            },
        )
        self.assertEqual(snapshot.drift_status, 'INITIAL')

    def test_tuning_context_snapshot_same_fingerprint_is_no_change(self):
        create_tuning_context_snapshot(
            source_scope='runtime_feedback',
            source_run_id=102,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'samefp',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 1},
            },
        )
        snapshot = create_tuning_context_snapshot(
            source_scope='runtime_feedback',
            source_run_id=103,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'samefp',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 2},
            },
        )
        self.assertEqual(snapshot.drift_status, 'NO_CHANGE')

    def test_tuning_context_snapshot_same_profile_different_fingerprint_is_minor_change(self):
        create_tuning_context_snapshot(
            source_scope='operating_mode',
            source_run_id=201,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'fp1',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 1},
            },
        )
        snapshot = create_tuning_context_snapshot(
            source_scope='operating_mode',
            source_run_id=202,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'fp2',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 2},
            },
        )
        self.assertEqual(snapshot.drift_status, 'MINOR_CONTEXT_CHANGE')

    def test_tuning_context_snapshot_different_profile_is_profile_change(self):
        create_tuning_context_snapshot(
            source_scope='mode_stabilization',
            source_run_id=301,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v1',
                'tuning_profile_fingerprint': 'fp1',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 1},
            },
        )
        snapshot = create_tuning_context_snapshot(
            source_scope='mode_stabilization',
            source_run_id=302,
            tuning_context={
                'tuning_profile_name': 'runtime_conservative_v2',
                'tuning_profile_fingerprint': 'fp2',
                'tuning_profile_summary': 'test',
                'tuning_effective_values': {'x': 2},
            },
        )
        self.assertEqual(snapshot.drift_status, 'PROFILE_CHANGE')

    def test_tuning_context_drift_summary_endpoint(self):
        RuntimeTuningContextSnapshot.objects.create(
            source_scope='mode_enforcement',
            source_run_id=401,
            tuning_profile_name='runtime_conservative_v1',
            tuning_profile_fingerprint='fp1',
            tuning_profile_summary='test',
            effective_values={'x': 1},
            drift_status='INITIAL',
            drift_summary='first',
        )
        response = self.client.get(reverse('runtime_governor_v2:tuning_context_drift_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('total_snapshots', payload)
        self.assertIn('status_counts', payload)
        self.assertIn('latest_by_scope', payload)

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

    def _create_ticks(self, *, count: int, status: str):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        for index in range(count):
            from apps.mission_control.models import AutonomousRuntimeTick

            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index + 1, tick_status=status)

    def _create_feedback_decision(self, decision_type: str, *, backlog_pressure_state: str = 'NORMAL') -> RuntimeFeedbackDecision:
        from apps.runtime_governor.models import RuntimeDiagnosticReview, RuntimePerformanceSnapshot

        snapshot = RuntimePerformanceSnapshot.objects.create(
            current_global_mode=get_runtime_state().metadata.get(GLOBAL_MODE_METADATA_KEY, 'BALANCED'),
            runtime_pressure_state='NORMAL',
            signal_quality_state='NORMAL',
            reason_codes=['test_feedback_signal'],
            metadata={
                'safety_posture': 'NORMAL',
                'governance_backlog_pressure_state': backlog_pressure_state,
            },
        )
        diagnostic = RuntimeDiagnosticReview.objects.create(
            linked_performance_snapshot=snapshot,
            diagnostic_type='HEALTHY_RUNTIME',
            diagnostic_severity='INFO',
            diagnostic_summary='test diagnostic',
            reason_codes=['test_diagnostic'],
        )
        return RuntimeFeedbackDecision.objects.create(
            linked_performance_snapshot=snapshot,
            linked_diagnostic_review=diagnostic,
            decision_type=decision_type,
            decision_status='PROPOSED',
            auto_applicable=True,
            decision_summary='test feedback decision',
            reason_codes=['test_feedback_decision'],
        )

    def _seed_governance_backlog_pressure(self, state: str):
        GovernanceBacklogPressureSnapshot.objects.create(
            governance_backlog_pressure_state=state,
            open_item_count=10,
            overdue_count=2,
            pressure_score=1,
            snapshot_summary=f'test backlog pressure {state}',
            reason_codes=[f'test_{state.lower()}'],
        )

    def test_runtime_feedback_losses_trigger_recovery_recommendation(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        AutonomousSessionHealthSnapshot.objects.create(
            linked_session=session,
            session_health_status=AutonomousSessionHealthStatus.CAUTION,
            recent_loss_count=3,
        )
        response = self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        recommendation = RuntimeFeedbackRecommendation.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'ENTER_RECOVERY_MODE')
        self.assertEqual(recommendation.recommendation_type, 'ENTER_RECOVERY_MODE_FOR_LOSS_PRESSURE')

    def test_runtime_feedback_quiet_runtime_shifts_monitor_only(self):
        self._create_ticks(count=3, status='SKIPPED')
        response = self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'SHIFT_TO_MONITOR_ONLY')

    def test_runtime_feedback_overtrading_pressure_shifts_conservative(self):
        for _ in range(8):
            self._seed_exposure_decision(PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES)
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        from apps.autonomous_trader.models import AutonomousExecutionDecision, AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousDispatchRecord
        market = Market.objects.create(provider=self.provider, provider_market_id='feedback-overtrading', title='Feedback overtrading', status='open')
        intake_run = AutonomousExecutionIntakeRun.objects.create()
        for _ in range(8):
            candidate = AutonomousExecutionIntakeCandidate.objects.create(intake_run=intake_run, linked_market=market)
            execution_decision = AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')
            AutonomousDispatchRecord.objects.create(linked_execution_decision=execution_decision, dispatch_status='DISPATCHED')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'SHIFT_TO_MORE_CONSERVATIVE_MODE')

    def test_runtime_feedback_relaxes_recovery_to_caution_after_improvement(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), 'global_operating_mode': 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        response = self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'RELAX_TO_CAUTION')

    def test_runtime_feedback_backlog_caution_adds_conservative_bias(self):
        self._seed_governance_backlog_pressure('CAUTION')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'SHIFT_TO_MORE_CONSERVATIVE_MODE')
        self.assertIn('backlog_caution_bias_conservative', decision.reason_codes)

    def test_runtime_feedback_backlog_high_blocks_relax_from_recovery(self):
        self._seed_governance_backlog_pressure('HIGH')
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'REDUCE_ADMISSION_AND_CADENCE')
        self.assertIn('backlog_high_relaxation_guard', decision.reason_codes)

    def test_runtime_feedback_high_manual_review_bias_uses_tuning_profile(self):
        self._seed_governance_backlog_pressure('HIGH')
        with patch(
            'apps.runtime_governor.runtime_feedback.services.feedback.get_runtime_conservative_tuning_profile',
            return_value=replace(DEFAULT_CONSERVATIVE_TUNING_PROFILE, high_backlog_manual_review_bias=False),
        ):
            self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertNotIn('backlog_high_manual_review_bias', decision.reason_codes)

    def test_runtime_feedback_backlog_critical_biases_manual_review_or_monitor_only(self):
        self._seed_governance_backlog_pressure('CRITICAL')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertIn(decision.decision_type, {'REQUIRE_MANUAL_RUNTIME_REVIEW', 'SHIFT_TO_MONITOR_ONLY'})
        self.assertIn('backlog_critical_manual_review_bias', decision.reason_codes)

    def test_runtime_feedback_backlog_normal_keeps_base_behavior(self):
        self._seed_governance_backlog_pressure('NORMAL')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'KEEP_CURRENT_GLOBAL_MODE')

    def test_runtime_feedback_summary_includes_governance_backlog_pressure(self):
        self._seed_governance_backlog_pressure('HIGH')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:runtime_feedback_summary'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['governance_backlog_pressure_state'], 'HIGH')

    def test_runtime_feedback_summary_endpoint(self):
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:runtime_feedback_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('feedback_runs', payload)
        self.assertIn('tuning_profile_name', payload)
        self.assertIn('tuning_effective_values', payload)
        self.assertIn('tuning_guardrail_summary', payload)

    def test_runtime_feedback_apply_recovery_recommendation_switches_mode(self):
        session = AutonomousRuntimeSession.objects.create(session_status=AutonomousRuntimeSessionStatus.RUNNING, runtime_mode='PAPER_AUTO')
        AutonomousSessionHealthSnapshot.objects.create(
            linked_session=session,
            session_health_status=AutonomousSessionHealthStatus.CAUTION,
            recent_loss_count=3,
        )
        feedback_response = self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(feedback_response.status_code, 200)
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        apply_response = self.client.post(reverse('runtime_governor_v2:apply_runtime_feedback_decision', kwargs={'decision_id': decision.id}), format='json')
        self.assertEqual(apply_response.status_code, 200)
        apply_record = RuntimeFeedbackApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.applied_mode, 'RECOVERY_MODE')

    def test_runtime_feedback_apply_relax_can_shift_to_caution(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), 'global_operating_mode': 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'RELAX_TO_CAUTION')
        self.client.post(reverse('runtime_governor_v2:apply_runtime_feedback_decision', kwargs={'decision_id': decision.id}), format='json')
        apply_record = RuntimeFeedbackApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.record_status, 'BLOCKED')

    def test_runtime_feedback_apply_manual_review_blocks_auto_apply(self):
        self._create_ticks(count=4, status='BLOCKED')
        response = self.client.post(
            reverse('runtime_governor_v2:run_runtime_feedback_review'),
            {'triggered_by': 'test', 'auto_apply': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        decision.decision_type = 'REQUIRE_MANUAL_RUNTIME_REVIEW'
        decision.auto_applicable = False
        decision.save(update_fields=['decision_type', 'auto_applicable', 'updated_at'])
        run_response = self.client.post(
            reverse('runtime_governor_v2:run_runtime_feedback_apply_review'),
            {'triggered_by': 'test', 'auto_apply': True},
            format='json',
        )
        self.assertEqual(run_response.status_code, 200)
        apply_decision = RuntimeFeedbackApplyDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_decision.apply_type, 'APPLY_MANUAL_REVIEW_ONLY')

    def test_runtime_feedback_apply_refreshes_enforcement_on_mode_change(self):
        RuntimeFeedbackApplyRecord.objects.all().delete()
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'BALANCED'}
        state.save(update_fields=['metadata', 'updated_at'])
        state.__class__.objects.filter(pk=state.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        self._create_ticks(count=3, status='SKIPPED')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.client.post(reverse('runtime_governor_v2:apply_runtime_feedback_decision', kwargs={'decision_id': decision.id}), format='json')
        apply_record = RuntimeFeedbackApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertTrue(apply_record.enforcement_refreshed)
        self.assertTrue(GlobalModeEnforcementRun.objects.exists())

    def test_runtime_feedback_apply_summary_endpoint(self):
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_apply_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:runtime_feedback_apply_summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('apply_runs', response.json())

    def test_mode_stabilization_entry_to_recovery_allows_fast(self):
        self._create_feedback_decision('ENTER_RECOVERY_MODE')
        response = self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.decision_type, 'ALLOW_MODE_SWITCH')

    def test_mode_stabilization_relax_from_recovery_is_deferred_when_early(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        self._create_feedback_decision('RELAX_TO_CAUTION', backlog_pressure_state='HIGH')
        response = self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        self.assertEqual(response.status_code, 200)
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertIn(decision.decision_type, {'DEFER_MODE_SWITCH', 'KEEP_CURRENT_MODE_FOR_DWELL'})
        review = RuntimeModeStabilityReview.objects.order_by('-created_at', '-id').first()
        self.assertIn(review.review_type, {'EARLY_RELAX_ATTEMPT', 'INSUFFICIENT_DWELL_TIME'})

    def test_mode_stabilization_backlog_high_extends_relaxation_dwell(self):
        self._seed_governance_backlog_pressure('HIGH')
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        state.__class__.objects.filter(pk=state.pk).update(updated_at=timezone.now() - timedelta(minutes=10))
        self._create_feedback_decision('RELAX_TO_CAUTION', backlog_pressure_state='HIGH')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertIn(decision.decision_type, {'DEFER_MODE_SWITCH', 'KEEP_CURRENT_MODE_FOR_DWELL'})

    def test_mode_stabilization_high_dwell_multiplier_uses_tuning_profile(self):
        self._seed_governance_backlog_pressure('HIGH')
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        state.__class__.objects.filter(pk=state.pk).update(updated_at=timezone.now() - timedelta(minutes=31))
        self._create_feedback_decision('RELAX_TO_CAUTION', backlog_pressure_state='HIGH')
        with patch(
            'apps.runtime_governor.services.stability_review.get_runtime_conservative_tuning_profile',
            return_value=replace(DEFAULT_CONSERVATIVE_TUNING_PROFILE, high_backlog_relax_dwell_multiplier=1.0),
        ):
            self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        review = RuntimeModeStabilityReview.objects.order_by('-created_at', '-id').first()
        self.assertEqual(review.review_type, 'SAFE_RELAXATION_WINDOW')

    def test_mode_stabilization_critical_relax_block_uses_tuning_profile(self):
        self._seed_governance_backlog_pressure('CRITICAL')
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        state.__class__.objects.filter(pk=state.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        self._create_feedback_decision('RELAX_TO_CAUTION', backlog_pressure_state='CRITICAL')
        with patch(
            'apps.runtime_governor.services.stability_review.get_runtime_conservative_tuning_profile',
            return_value=replace(DEFAULT_CONSERVATIVE_TUNING_PROFILE, critical_backlog_blocks_relax=False),
        ):
            self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        review = RuntimeModeStabilityReview.objects.order_by('-created_at', '-id').first()
        self.assertEqual(review.review_type, 'SAFE_RELAXATION_WINDOW')

    def test_mode_stabilization_flapping_risk_blocks_or_defers(self):
        from apps.runtime_governor.models import RuntimeFeedbackApplyDecision, RuntimeFeedbackApplyRecord

        for _ in range(4):
            feedback = self._create_feedback_decision('SHIFT_TO_MORE_CONSERVATIVE_MODE')
            apply_decision = RuntimeFeedbackApplyDecision.objects.create(
                linked_feedback_decision=feedback,
                current_mode='BALANCED',
                target_mode='CAUTION',
                apply_type='APPLY_SHIFT_TO_CAUTION',
                apply_status='APPLIED',
                auto_applicable=True,
                apply_summary='test apply',
            )
            RuntimeFeedbackApplyRecord.objects.create(
                linked_apply_decision=apply_decision,
                record_status='APPLIED',
                previous_mode='BALANCED',
                applied_mode='CAUTION',
                metadata={'mode_switched': True},
            )
        self._create_feedback_decision('SHIFT_TO_MONITOR_ONLY')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertIn(decision.decision_type, {'BLOCK_MODE_SWITCH', 'DEFER_MODE_SWITCH'})

    def test_mode_stabilization_hard_block_transition_is_allowed(self):
        decision = self._create_feedback_decision('SHIFT_TO_MORE_CONSERVATIVE_MODE')
        decision.linked_performance_snapshot.runtime_pressure_state = 'CRITICAL'
        decision.linked_performance_snapshot.metadata = {'safety_posture': 'HARD_BLOCK'}
        decision.linked_performance_snapshot.save(update_fields=['runtime_pressure_state', 'metadata', 'updated_at'])
        decision.reason_codes = ['safety_hard_block_trigger']
        decision.save(update_fields=['reason_codes', 'updated_at'])
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        latest = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(latest.decision_type, 'ALLOW_MODE_SWITCH')

    def test_mode_stabilization_summary_endpoint(self):
        self._create_feedback_decision('ENTER_RECOVERY_MODE')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        response = self.client.get(reverse('runtime_governor_v2:mode_stabilization_summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('runs', payload)
        self.assertIn('tuning_profile_name', payload)
        self.assertIn('tuning_effective_values', payload)
        self.assertIn('tuning_guardrail_summary', payload)

    def test_summary_endpoints_keep_existing_fields_while_adding_tuning_context(self):
        self.client.post(reverse('runtime_governor_v2:run_runtime_feedback_review'), {'triggered_by': 'test'}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_operating_mode_review'), {'triggered_by': 'test', 'auto_apply': True}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        self.client.post(reverse('runtime_governor_v2:run_mode_enforcement_review'), {'triggered_by': 'test'}, format='json')

        feedback = self.client.get(reverse('runtime_governor_v2:runtime_feedback_summary')).json()
        operating = self.client.get(reverse('runtime_governor_v2:operating_mode_summary')).json()
        stabilization = self.client.get(reverse('runtime_governor_v2:mode_stabilization_summary')).json()
        enforcement = self.client.get(reverse('runtime_governor_v2:mode_enforcement_summary')).json()

        self.assertIn('feedback_runs', feedback)
        self.assertIn('active_mode', operating)
        self.assertIn('runs', stabilization)
        self.assertIn('current_mode', enforcement)

    def test_apply_stabilized_transition_allows_mode_switch(self):
        self._create_feedback_decision('ENTER_RECOVERY_MODE')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        response = self.client.post(
            reverse('runtime_governor_v2:apply_stabilized_mode_transition', kwargs={'decision_id': decision.id}),
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        apply_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.apply_status, 'APPLIED')
        self.assertTrue(apply_record.enforcement_refreshed)
        state = get_runtime_state()
        self.assertEqual((state.metadata or {}).get(GLOBAL_MODE_METADATA_KEY), 'RECOVERY_MODE')

    def test_apply_stabilized_transition_deferred_is_blocked(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        self._create_feedback_decision('RELAX_TO_CAUTION')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertIn(decision.decision_type, {'DEFER_MODE_SWITCH', 'KEEP_CURRENT_MODE_FOR_DWELL'})
        self.client.post(reverse('runtime_governor_v2:apply_stabilized_mode_transition', kwargs={'decision_id': decision.id}), format='json')
        apply_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.apply_status, 'BLOCKED')
        self.assertFalse(apply_record.enforcement_refreshed)

    def test_apply_stabilized_transition_manual_and_blocked_decisions_are_blocked(self):
        self._create_feedback_decision('ENTER_RECOVERY_MODE')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        latest = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        latest.decision_type = 'REQUIRE_MANUAL_STABILITY_REVIEW'
        latest.auto_applicable = False
        latest.save(update_fields=['decision_type', 'auto_applicable', 'updated_at'])
        self.client.post(reverse('runtime_governor_v2:apply_stabilized_mode_transition', kwargs={'decision_id': latest.id}), format='json')
        manual_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(manual_record.apply_status, 'BLOCKED')

        latest.decision_type = 'BLOCK_MODE_SWITCH'
        latest.save(update_fields=['decision_type', 'updated_at'])
        self.client.post(reverse('runtime_governor_v2:apply_stabilized_mode_transition', kwargs={'decision_id': latest.id}), format='json')
        blocked_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(blocked_record.apply_status, 'BLOCKED')
        self.assertEqual(blocked_record.linked_transition_decision_id, latest.id)

    def test_apply_stabilized_transition_skips_without_mode_change_and_no_enforcement_refresh(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'CAUTION'}
        state.save(update_fields=['metadata', 'updated_at'])
        state.__class__.objects.filter(pk=state.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        self._create_feedback_decision('SHIFT_TO_MORE_CONSERVATIVE_MODE')
        self.client.post(reverse('runtime_governor_v2:run_mode_stabilization_review'), {'triggered_by': 'test'}, format='json')
        decision = RuntimeModeTransitionDecision.objects.order_by('-created_at', '-id').first()
        self.assertEqual(decision.linked_transition_snapshot.target_mode, 'CAUTION')
        self.client.post(reverse('runtime_governor_v2:apply_stabilized_mode_transition', kwargs={'decision_id': decision.id}), format='json')
        apply_record = RuntimeModeTransitionApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.apply_status, 'SKIPPED')
        self.assertFalse(apply_record.enforcement_refreshed)

    def test_runtime_feedback_apply_consults_mode_stabilization_gate(self):
        state = get_runtime_state()
        state.metadata = {**(state.metadata or {}), GLOBAL_MODE_METADATA_KEY: 'RECOVERY_MODE'}
        state.save(update_fields=['metadata', 'updated_at'])
        self._create_feedback_decision('RELAX_TO_CAUTION')
        feedback_decision = RuntimeFeedbackDecision.objects.order_by('-created_at', '-id').first()
        self.client.post(reverse('runtime_governor_v2:apply_runtime_feedback_decision', kwargs={'decision_id': feedback_decision.id}), format='json')
        apply_record = RuntimeFeedbackApplyRecord.objects.order_by('-created_at', '-id').first()
        self.assertEqual(apply_record.record_status, 'BLOCKED')
        self.assertIn('stabilization_transition_decision_id', apply_record.metadata)
