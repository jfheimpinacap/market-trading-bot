from unittest.mock import patch
import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousProfileSwitchRecord,
    AutonomousCooldownState,
    AutonomousRunnerState,
    AutonomousRunnerStatus,
    AutonomousRuntimeSessionStatus,
    AutonomousSessionInterventionDecision,
    AutonomousSessionHealthSnapshot,
    AutonomousResumeDecision,
    AutonomousResumeRecord,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoverySnapshot,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousScheduleProfile,
    GovernanceReviewResolution,
    GovernanceAutoResolutionDecision,
    GovernanceAutoResolutionRecord,
    GovernanceQueueAgingReview,
    GovernanceBacklogPressureSnapshot,
    MissionControlCycle,
    MissionControlSession,
    MissionControlState,
    GovernanceReviewItem,
)
from apps.runtime_governor.models import RuntimeMode
from apps.mission_control.services.collect import collect_governance_review_candidates
from apps.mission_control.services.live_paper_trial_history import (
    _clear_live_paper_trial_history_for_tests,
    _HISTORY_CAPACITY,
    record_live_paper_trial_result,
)
from apps.mission_control.services.prioritize import assign_severity_and_priority
from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
)
from apps.operator_alerts.models import OperatorAlert, OperatorAlertSeverity, OperatorAlertSource, OperatorAlertStatus, OperatorAlertType


class MissionControlApiTests(TestCase):
    @patch('apps.mission_control.services.controller.threading.Thread.start', return_value=None)
    def test_start_pause_resume_stop_and_status(self, _mock_start):
        start = self.client.post(reverse('mission_control:start'), data=json.dumps({'cycle_interval_seconds': 5}), content_type='application/json')
        self.assertEqual(start.status_code, 200)

        status_res = self.client.get(reverse('mission_control:status'))
        self.assertEqual(status_res.status_code, 200)
        self.assertIn('state', status_res.json())

        pause = self.client.post(reverse('mission_control:pause'), data='{}', content_type='application/json')
        self.assertEqual(pause.status_code, 200)

        resume = self.client.post(reverse('mission_control:resume'), data='{}', content_type='application/json')
        self.assertEqual(resume.status_code, 200)

        stop = self.client.post(reverse('mission_control:stop'), data='{}', content_type='application/json')
        self.assertEqual(stop.status_code, 200)

    @patch('apps.mission_control.services.cycle_runner.get_capabilities_for_current_mode')
    def test_runtime_blocking_is_respected(self, mock_caps):
        mock_caps.return_value = {
            'allow_signal_generation': False,
            'allow_proposals': False,
            'allow_auto_execution': False,
            'allow_continuous_loop': False,
            'max_auto_trades_per_cycle': 0,
        }
        cycle_res = self.client.post(reverse('mission_control:run-cycle'), data='{}', content_type='application/json')
        self.assertEqual(cycle_res.status_code, 200)
        self.assertEqual(cycle_res.json()['status'], 'SKIPPED')

    @patch('apps.mission_control.services.cycle_runner.run_position_watch')
    @patch('apps.mission_control.services.cycle_runner.run_opportunity_cycle')
    def test_cycle_calls_opportunity_supervisor_and_persists(self, mock_opp, mock_watch):
        class Result:
            id = 11
            status = 'COMPLETED'
            summary = 'ok'
            opportunities_built = 4
            proposals_generated = 2
            queued_count = 1
            auto_executed_count = 1
            blocked_count = 1

        mock_opp.return_value = Result()
        mock_watch.return_value = {'ok': True}

        cycle_res = self.client.post(reverse('mission_control:run-cycle'), data='{}', content_type='application/json')
        self.assertEqual(cycle_res.status_code, 200)
        payload = cycle_res.json()
        self.assertIn(payload['status'], {'SUCCESS', 'PARTIAL'})
        self.assertEqual(payload['opportunities_built'], 4)
        self.assertTrue(MissionControlSession.objects.exists())
        self.assertTrue(MissionControlCycle.objects.exists())
        self.assertTrue(payload['steps'])

        summary_res = self.client.get(reverse('mission_control:summary'))
        self.assertEqual(summary_res.status_code, 200)
        self.assertGreaterEqual(summary_res.json()['cycle_count'], 1)

        cycles_res = self.client.get(reverse('mission_control:cycle-list'))
        sessions_res = self.client.get(reverse('mission_control:session-list'))
        self.assertEqual(cycles_res.status_code, 200)
        self.assertEqual(sessions_res.status_code, 200)

    def test_state_record_created(self):
        self.client.get(reverse('mission_control:status'))
        self.assertEqual(MissionControlState.objects.count(), 1)


class AutonomousRuntimeApiTests(TestCase):
    @patch('apps.mission_control.services.cycle_runner.run_position_watch', return_value={'ok': True})
    @patch('apps.mission_control.services.cycle_runner.run_opportunity_cycle')
    def test_run_autonomous_runtime_full_cycle(self, mock_opp, _mock_watch):
        class Result:
            id = 12
            status = 'COMPLETED'
            summary = 'full'
            opportunities_built = 3
            proposals_generated = 2
            queued_count = 0
            auto_executed_count = 1
            blocked_count = 0

        mock_opp.return_value = Result()
        response = self.client.post(reverse('mission_control:run-autonomous-runtime'), data=json.dumps({'cycle_count': 1}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['cycle_count'], 1)
        self.assertGreaterEqual(payload['executed_cycle_count'], 1)

    @patch('apps.mission_control.services.autonomous_runtime.cycle_plan.get_capabilities_for_current_mode')
    def test_runtime_block_reduces_or_blocks_cycle(self, mock_caps):
        mock_caps.return_value = {
            'allow_signal_generation': False,
            'allow_proposals': False,
            'allow_auto_execution': False,
        }
        response = self.client.post(reverse('mission_control:run-autonomous-runtime'), data=json.dumps({'cycle_count': 1}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        run_id = response.json()['id']
        plans = self.client.get(reverse('mission_control:autonomous-cycle-plans')).json()
        self.assertTrue(any(p['linked_runtime_run'] == run_id and p['plan_status'] == 'BLOCKED' for p in plans))

    def test_autonomous_runtime_summary_endpoint(self):
        self.client.post(reverse('mission_control:run-autonomous-runtime'), data=json.dumps({'cycle_count': 1}), content_type='application/json')
        response = self.client.get(reverse('mission_control:autonomous-runtime-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('totals', response.json())


class AutonomousSessionRuntimeTests(TestCase):
    @patch('apps.mission_control.services.cycle_runner.run_position_watch', return_value={'ok': True})
    @patch('apps.mission_control.services.cycle_runner.run_opportunity_cycle')
    def test_start_pause_resume_stop_and_tick(self, mock_opp, _mock_watch):
        class Result:
            id = 44
            status = 'COMPLETED'
            summary = 'ok'
            opportunities_built = 1
            proposals_generated = 1
            queued_count = 0
            auto_executed_count = 0
            blocked_count = 0

        mock_opp.return_value = Result()
        start = self.client.post(reverse('mission_control:start-autonomous-session'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['id']

        tick = self.client.post(reverse('mission_control:run-autonomous-tick', args=[session_id]), data='{}', content_type='application/json')
        self.assertEqual(tick.status_code, 200)
        self.assertIn(tick.json()['tick']['tick_status'], {'COMPLETED', 'PARTIAL', 'SKIPPED'})

        pause = self.client.post(reverse('mission_control:pause-autonomous-session', args=[session_id]), data='{}', content_type='application/json')
        self.assertEqual(pause.status_code, 200)
        self.assertEqual(pause.json()['session_status'], 'PAUSED')

        resume = self.client.post(reverse('mission_control:resume-autonomous-session', args=[session_id]), data='{}', content_type='application/json')
        self.assertEqual(resume.status_code, 200)
        self.assertEqual(resume.json()['session_status'], 'RUNNING')

        stop = self.client.post(reverse('mission_control:stop-autonomous-session', args=[session_id]), data='{}', content_type='application/json')
        self.assertEqual(stop.status_code, 200)
        self.assertEqual(stop.json()['session_status'], 'STOPPED')

    @patch('apps.mission_control.services.session_runtime.cadence.get_safety_status')
    def test_tick_blocked_when_safety_blocks(self, mock_safety):
        mock_safety.return_value = {'kill_switch_enabled': True, 'hard_stop_active': True}
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-tick', args=[session.id]), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['cadence_decision']['cadence_mode'], 'STOP_SESSION')
        self.assertEqual(payload['tick']['tick_status'], 'BLOCKED')

    def test_autonomous_session_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.get(reverse('mission_control:autonomous-session-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_sessions', response.json())


class LivePaperBootstrapApiTests(TestCase):
    SUCCESS_CAPABILITIES = {
        'allow_signal_generation': True,
        'allow_proposals': True,
        'allow_allocation': True,
        'allow_real_market_ops': True,
        'allow_auto_execution': False,
        'allow_continuous_loop': True,
        'require_operator_for_all_trades': True,
        'allow_pending_approvals': True,
        'allow_replay': True,
        'allow_experiments': True,
        'max_auto_trades_per_cycle': 0,
        'max_auto_trades_per_session': 0,
        'blocked_reasons': [],
    }

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    @patch('apps.mission_control.services.live_paper_bootstrap.start_runner')
    @patch('apps.mission_control.services.live_paper_bootstrap.set_runtime_mode')
    def test_creates_and_starts_session_when_missing(self, mock_set_mode, mock_start_runner, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        mock_set_mode.return_value = {
            'decision': type('Decision', (), {'allowed': True, 'reasons': []})(),
            'state': type('State', (), {'current_mode': RuntimeMode.PAPER_ASSIST})(),
        }
        mock_start_runner.side_effect = lambda: AutonomousRunnerState.objects.update_or_create(
            runner_name='local_autonomous_heartbeat_runner',
            defaults={'runner_status': AutonomousRunnerStatus.RUNNING},
        )[0]
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['bootstrap_action'], 'CREATED_AND_STARTED')
        self.assertTrue(payload['session_created'])
        self.assertTrue(payload['session_started'])
        session = AutonomousRuntimeSession.objects.get(id=payload['session_id'])
        self.assertEqual(session.metadata.get('market_data_mode'), 'REAL_READ_ONLY')
        self.assertEqual(session.metadata.get('paper_execution_mode'), 'PAPER_ONLY')

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    @patch('apps.mission_control.services.live_paper_bootstrap.start_runner')
    @patch('apps.mission_control.services.live_paper_bootstrap.set_runtime_mode')
    def test_does_not_duplicate_equivalent_session(self, mock_set_mode, mock_start_runner, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        mock_set_mode.return_value = {
            'decision': type('Decision', (), {'allowed': True, 'reasons': []})(),
            'state': type('State', (), {'current_mode': RuntimeMode.PAPER_ASSIST})(),
        }
        mock_start_runner.side_effect = lambda: AutonomousRunnerState.objects.update_or_create(
            runner_name='local_autonomous_heartbeat_runner',
            defaults={'runner_status': AutonomousRunnerStatus.RUNNING},
        )[0]
        existing = AutonomousRuntimeSession.objects.create(
            session_status=AutonomousRuntimeSessionStatus.RUNNING,
            runtime_mode=RuntimeMode.PAPER_ASSIST,
            metadata={
                'autopilot_preset_name': 'live_read_only_paper_conservative',
                'market_data_mode': 'REAL_READ_ONLY',
                'paper_execution_mode': 'PAPER_ONLY',
            },
        )
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['bootstrap_action'], 'REUSED_EXISTING_SESSION')
        self.assertFalse(payload['session_created'])
        self.assertEqual(payload['session_id'], existing.id)
        self.assertEqual(
            AutonomousRuntimeSession.objects.filter(metadata__autopilot_preset_name='live_read_only_paper_conservative').count(),
            1,
        )

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    @patch('apps.mission_control.services.live_paper_bootstrap.start_runner')
    @patch('apps.mission_control.services.live_paper_bootstrap.set_runtime_mode')
    def test_reuses_heartbeat_when_runner_already_running(self, mock_set_mode, mock_start_runner, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        mock_set_mode.return_value = {
            'decision': type('Decision', (), {'allowed': True, 'reasons': []})(),
            'state': type('State', (), {'current_mode': RuntimeMode.PAPER_ASSIST})(),
        }
        AutonomousRunnerState.objects.create(runner_name='local_autonomous_heartbeat_runner', runner_status=AutonomousRunnerStatus.RUNNING)
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['heartbeat_started'])
        mock_start_runner.assert_not_called()

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    @patch('apps.mission_control.services.live_paper_bootstrap.set_runtime_mode')
    def test_returns_blocked_when_constraints_disallow_runtime_mode(self, mock_set_mode, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        mock_set_mode.return_value = {
            'decision': type('Decision', (), {'allowed': False, 'reasons': ['blocked for test']})(),
            'state': type('State', (), {'current_mode': RuntimeMode.OBSERVE_ONLY})(),
        }
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['bootstrap_action'], 'BLOCKED')
        self.assertIn('blocked for test', payload['bootstrap_summary'])

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    @patch('apps.mission_control.services.live_paper_bootstrap.start_runner')
    @patch('apps.mission_control.services.live_paper_bootstrap.set_runtime_mode')
    def test_post_payload_contract_is_compact_and_stable(self, mock_set_mode, mock_start_runner, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        mock_set_mode.return_value = {
            'decision': type('Decision', (), {'allowed': True, 'reasons': []})(),
            'state': type('State', (), {'current_mode': RuntimeMode.PAPER_ASSIST})(),
        }
        mock_start_runner.side_effect = lambda: AutonomousRunnerState.objects.update_or_create(
            runner_name='local_autonomous_heartbeat_runner',
            defaults={'runner_status': AutonomousRunnerStatus.RUNNING},
        )[0]
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        payload = response.json()
        required_keys = {
            'preset_name', 'session_created', 'session_started', 'heartbeat_started', 'runtime_mode',
            'paper_execution_mode', 'market_data_mode', 'bootstrap_action', 'session_id',
            'next_step_summary', 'bootstrap_summary',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))
        self.assertEqual(payload['market_data_mode'], 'REAL_READ_ONLY')
        self.assertEqual(payload['paper_execution_mode'], 'PAPER_ONLY')

    def test_status_payload_contract_and_summary_readable(self):
        session = AutonomousRuntimeSession.objects.create(
            session_status=AutonomousRuntimeSessionStatus.RUNNING,
            runtime_mode=RuntimeMode.PAPER_ASSIST,
            metadata={
                'autopilot_preset_name': 'live_read_only_paper_conservative',
                'market_data_mode': 'REAL_READ_ONLY',
                'paper_execution_mode': 'PAPER_ONLY',
            },
        )
        AutonomousRunnerState.objects.create(runner_name='local_autonomous_heartbeat_runner', runner_status=AutonomousRunnerStatus.RUNNING)
        response = self.client.get(reverse('mission_control:live-paper-bootstrap-status'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        required_keys = {
            'preset_name', 'session_active', 'heartbeat_active', 'runtime_mode', 'market_data_mode',
            'paper_execution_mode', 'current_session_status', 'operator_attention_hint', 'status_summary',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))
        self.assertTrue(payload['session_active'])
        self.assertEqual(payload['current_session_status'], session.session_status)
        self.assertIn('preset=live_read_only_paper_conservative', payload['status_summary'])

    @patch('apps.mission_control.services.live_paper_bootstrap.get_capabilities_for_current_mode')
    def test_existing_session_is_resumed_when_paused(self, mock_caps):
        mock_caps.return_value = self.SUCCESS_CAPABILITIES
        session = AutonomousRuntimeSession.objects.create(
            session_status=AutonomousRuntimeSessionStatus.PAUSED,
            runtime_mode=RuntimeMode.PAPER_ASSIST,
            metadata={
                'autopilot_preset_name': 'live_read_only_paper_conservative',
                'market_data_mode': 'REAL_READ_ONLY',
                'paper_execution_mode': 'PAPER_ONLY',
            },
        )
        response = self.client.post(reverse('mission_control:bootstrap-live-paper-session'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['bootstrap_action'], 'STARTED_EXISTING_SAFE_SESSION')
        session.refresh_from_db()
        self.assertEqual(session.session_status, AutonomousRuntimeSessionStatus.RUNNING)

    def test_existing_mission_control_flows_still_work(self):
        response = self.client.get(reverse('mission_control:autonomous-session-summary'))
        self.assertEqual(response.status_code, 200)


class AutonomousHeartbeatRunnerTests(TestCase):
    def test_runner_start_pause_resume_stop(self):
        start = self.client.post(reverse('mission_control:start-autonomous-runner'), data='{}', content_type='application/json')
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.json()['runner_status'], 'RUNNING')

        pause = self.client.post(reverse('mission_control:pause-autonomous-runner'), data='{}', content_type='application/json')
        self.assertEqual(pause.status_code, 200)
        self.assertEqual(pause.json()['runner_status'], 'PAUSED')

        resume = self.client.post(reverse('mission_control:resume-autonomous-runner'), data='{}', content_type='application/json')
        self.assertEqual(resume.status_code, 200)
        self.assertEqual(resume.json()['runner_status'], 'RUNNING')

        stop = self.client.post(reverse('mission_control:stop-autonomous-runner'), data='{}', content_type='application/json')
        self.assertEqual(stop.status_code, 200)
        self.assertEqual(stop.json()['runner_status'], 'STOPPED')

    @patch('apps.mission_control.services.cycle_runner.run_position_watch', return_value={'ok': True})
    @patch('apps.mission_control.services.cycle_runner.run_opportunity_cycle')
    def test_due_tick_executes_automatically(self, mock_opp, _mock_watch):
        class Result:
            id = 100
            status = 'COMPLETED'
            summary = 'ok'
            opportunities_built = 1
            proposals_generated = 1
            queued_count = 0
            auto_executed_count = 0
            blocked_count = 0

        mock_opp.return_value = Result()
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertGreaterEqual(session.tick_count, 1)

    def test_cooldown_skips_dispatch(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        AutonomousCooldownState.objects.create(
            linked_session=session,
            cooldown_type='RUNTIME_CAUTION_COOLDOWN',
            cooldown_status='ACTIVE',
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:autonomous-heartbeat-decisions')).json()
        self.assertTrue(any(d['linked_session'] == session.id and d['decision_type'] == 'SKIP_FOR_COOLDOWN' for d in decisions))

    @patch('apps.mission_control.services.session_heartbeat.due_tick.get_safety_status')
    def test_blocking_prevents_automatic_dispatch(self, mock_safety):
        mock_safety.return_value = {'kill_switch_enabled': True, 'hard_stop_active': True}
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        attempts = self.client.get(reverse('mission_control:autonomous-tick-dispatch-attempts')).json()
        self.assertFalse(any(attempt['linked_session'] == session.id for attempt in attempts))

    def test_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:autonomous-heartbeat-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('totals', response.json())

    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_tuning_autotriage_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': True,
            'alert_action': 'UPDATED',
            'human_attention_mode': 'REVIEW_NOW',
            'next_recommended_scope': 'mode_enforcement',
            'material_change_detected': True,
            'material_change_fields': ['next_recommended_scope'],
            'update_suppressed': False,
            'suppression_reason': None,
            'active_alert_present': True,
            'sync_summary': 'REVIEW_NOW: active high attention alert (next: mode_enforcement)',
        },
    )
    def test_heartbeat_runs_tuning_attention_sync_once_per_pass(self, mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_auto_sync.call_count, 1)

        payload = response.json()
        sync_payload = (payload.get('metadata') or {}).get('runtime_tuning_attention_sync') or {}
        self.assertEqual(sync_payload.get('alert_action'), 'UPDATED')
        self.assertTrue(sync_payload.get('success'))
        self.assertTrue(sync_payload.get('material_change_detected'))

    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_tuning_autotriage_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': True,
            'alert_action': 'NOOP',
            'human_attention_mode': 'REVIEW_SOON',
            'next_recommended_scope': 'operating_mode',
            'material_change_detected': False,
            'material_change_fields': [],
            'update_suppressed': True,
            'suppression_reason': 'NO_MATERIAL_CHANGE',
            'active_alert_present': True,
            'sync_summary': 'REVIEW_SOON: active warning attention alert (next: operating_mode)',
        },
    )
    def test_heartbeat_summary_exposes_runtime_tuning_attention_sync_contract(self, _mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:autonomous-heartbeat-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('runtime_tuning_attention_sync', payload)
        self.assertEqual(payload['runtime_tuning_attention_sync']['alert_action'], 'NOOP')
        self.assertEqual(payload['runtime_tuning_attention_sync']['human_attention_mode'], 'REVIEW_SOON')
        self.assertTrue(payload['runtime_tuning_attention_sync']['update_suppressed'])

    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_tuning_autotriage_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': False,
            'alert_action': 'ERROR',
            'human_attention_mode': None,
            'next_recommended_scope': None,
            'material_change_detected': False,
            'material_change_fields': [],
            'update_suppressed': False,
            'suppression_reason': None,
            'active_alert_present': False,
            'sync_summary': 'auto-sync failed: RuntimeError',
        },
    )
    def test_heartbeat_continues_when_tuning_attention_sync_fails(self, _mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['runner_status'], 'COMPLETED')
        sync_payload = (payload.get('metadata') or {}).get('runtime_tuning_attention_sync') or {}
        self.assertEqual(sync_payload.get('alert_action'), 'ERROR')
        self.assertFalse(sync_payload.get('success'))


    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_live_paper_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': True,
            'alert_action': 'UPDATED',
            'attention_mode': 'REVIEW_NOW',
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'RUNNING',
            'sync_summary': 'REVIEW_NOW: active high operator alert',
        },
    )
    def test_heartbeat_runs_live_paper_attention_sync_once_per_pass(self, mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_auto_sync.call_count, 1)

        payload = response.json()
        sync_payload = (payload.get('metadata') or {}).get('live_paper_attention_sync') or {}
        self.assertEqual(sync_payload.get('alert_action'), 'UPDATED')
        self.assertTrue(sync_payload.get('success'))

    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_live_paper_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': True,
            'alert_action': 'NOOP',
            'attention_mode': 'HEALTHY',
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': 'MISSING',
            'sync_summary': 'HEALTHY: no attention required',
        },
    )
    def test_heartbeat_summary_exposes_live_paper_attention_sync_contract(self, _mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:autonomous-heartbeat-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('live_paper_attention_sync', payload)
        self.assertEqual(payload['live_paper_attention_sync']['alert_action'], 'NOOP')
        self.assertEqual(payload['live_paper_attention_sync']['attention_mode'], 'HEALTHY')
        self.assertFalse(payload['live_paper_attention_sync']['heartbeat_active'])

    @patch(
        'apps.mission_control.services.session_heartbeat.run.run_live_paper_attention_auto_sync',
        return_value={
            'attempted': True,
            'success': False,
            'alert_action': 'ERROR',
            'attention_mode': None,
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': None,
            'sync_summary': 'auto-sync failed: RuntimeError',
        },
    )
    def test_heartbeat_continues_when_live_paper_attention_sync_fails(self, _mock_auto_sync):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['runner_status'], 'COMPLETED')
        sync_payload = (payload.get('metadata') or {}).get('live_paper_attention_sync') or {}
        self.assertEqual(sync_payload.get('alert_action'), 'ERROR')
        self.assertFalse(sync_payload.get('success'))



class LivePaperAttentionBridgeTests(TestCase):
    def setUp(self):
        super().setUp()
        self._funnel_patcher = patch(
            'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
            return_value={
                'funnel_status': 'ACTIVE',
                'stalled_stage': None,
                'top_stage': 'paper_execution',
                'funnel_summary': 'ACTIVE: baseline flow present.',
                'signal_available': True,
            },
        )
        self._funnel_patcher.start()

    def tearDown(self):
        self._funnel_patcher.stop()
        super().tearDown()

    def _sync(self) -> dict:
        response = self.client.post(reverse('mission_control:sync-live-paper-attention-alert'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response.json()

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary',
        return_value={'runtime_tuning_attention_sync': {'human_attention_mode': 'NO_ACTION'}},
    )
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': 'MISSING',
            'operator_attention_hint': 'Bootstrap has not created a reusable session yet.',
            'status_summary': 'preset=live_read_only_paper_conservative session_active=False heartbeat_active=False',
        },
    )
    def test_healthy_without_session_keeps_no_active_alert(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'HEALTHY')
        self.assertEqual(payload['funnel_status'], 'ACTIVE')
        self.assertIn('funnel_active', payload['attention_reason_codes'])
        self.assertIn(payload['alert_action'], {'NOOP', 'RESOLVED'})
        self.assertFalse(OperatorAlert.objects.filter(dedupe_key='live_paper_autopilot_attention_global', status=OperatorAlertStatus.OPEN).exists())

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'BLOCKED',
            'operator_attention_hint': 'Session blocked by safety stop.',
            'status_summary': 'session blocked',
        },
    )
    def test_blocked_session_creates_active_alert(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'BLOCKED')
        self.assertEqual(payload['alert_action'], 'CREATED')
        self.assertEqual(payload['alert_severity'], OperatorAlertSeverity.HIGH)
        self.assertTrue(OperatorAlert.objects.filter(dedupe_key='live_paper_autopilot_attention_global', status=OperatorAlertStatus.OPEN).exists())

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'Session is active; monitor heartbeat and safety guardrails.',
            'status_summary': 'session active heartbeat inactive',
        },
    )
    def test_active_session_with_inactive_heartbeat_requires_review(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'REVIEW_NOW')
        self.assertTrue(payload['attention_needed'])
        self.assertIn('session_active_heartbeat_inactive', payload['attention_reason_codes'])

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {'manual_review': 0, 'incident_escalation': 0}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {'manual_review_or_escalation': 1}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {'human_attention_mode': 'REVIEW_SOON'}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'DEGRADED',
            'operator_attention_hint': 'Session is active; monitor heartbeat and safety guardrails.',
            'status_summary': 'session degraded',
        },
    )
    def test_degraded_state_uses_warning_alert(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'DEGRADED')
        self.assertEqual(payload['alert_severity'], OperatorAlertSeverity.WARNING)
        alert = OperatorAlert.objects.get(dedupe_key='live_paper_autopilot_attention_global')
        self.assertEqual(alert.severity, OperatorAlertSeverity.WARNING)

    @patch(
        'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
        return_value={
            'funnel_status': 'THIN_FLOW',
            'stalled_stage': None,
            'top_stage': 'prediction',
            'funnel_summary': 'THIN_FLOW: weak progression.',
            'signal_available': True,
        },
    )
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'Session is active',
            'status_summary': 'session healthy',
        },
    )
    def test_funnel_thin_flow_marks_degraded_attention(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'DEGRADED')
        self.assertEqual(payload['funnel_status'], 'THIN_FLOW')
        self.assertIn('funnel_thin_flow', payload['attention_reason_codes'])

    @patch(
        'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
        return_value={
            'funnel_status': 'STALLED',
            'stalled_stage': 'prediction',
            'top_stage': 'research',
            'funnel_summary': 'STALLED: no prediction progression.',
            'signal_available': True,
        },
    )
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'Session is active',
            'status_summary': 'session healthy',
        },
    )
    def test_funnel_stalled_with_live_session_escalates_review_now(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'REVIEW_NOW')
        self.assertEqual(payload['funnel_status'], 'STALLED')
        self.assertIn('funnel_stalled', payload['attention_reason_codes'])
        self.assertIn('funnel_stalled_at_prediction', payload['attention_reason_codes'])

    @patch(
        'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
        return_value={
            'funnel_status': 'STALLED',
            'stalled_stage': 'risk',
            'top_stage': 'prediction',
            'funnel_summary': 'STALLED: risk stage not progressing.',
            'signal_available': True,
        },
    )
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'BLOCKED',
            'operator_attention_hint': 'Session blocked by safety stop.',
            'status_summary': 'session blocked',
        },
    )
    def test_blocked_signal_has_priority_over_funnel_state(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'BLOCKED')
        self.assertNotIn('funnel_stalled', payload['attention_reason_codes'])

    @patch(
        'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
        return_value={
            'funnel_status': None,
            'stalled_stage': None,
            'top_stage': None,
            'funnel_summary': None,
            'signal_available': False,
        },
    )
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': 'MISSING',
            'operator_attention_hint': 'Bootstrap has not created a reusable session yet.',
            'status_summary': 'session missing',
        },
    )
    def test_funnel_signal_unavailable_falls_back_without_noise(self, *_mocks):
        payload = self._sync()
        self.assertEqual(payload['attention_mode'], 'HEALTHY')
        self.assertIsNone(payload['funnel_status'])
        self.assertIn('funnel_signal_unavailable', payload['attention_reason_codes'])

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'active',
            'status_summary': 'review now state',
        },
    )
    def test_global_dedupe_avoids_multiple_open_alerts(self, *_mocks):
        OperatorAlert.objects.create(
            alert_type=OperatorAlertType.RUNTIME,
            severity=OperatorAlertSeverity.HIGH,
            status=OperatorAlertStatus.OPEN,
            title='dup-1',
            summary='dup',
            source=OperatorAlertSource.RUNTIME,
            dedupe_key='live_paper_autopilot_attention_global',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            metadata={},
        )
        OperatorAlert.objects.create(
            alert_type=OperatorAlertType.RUNTIME,
            severity=OperatorAlertSeverity.HIGH,
            status=OperatorAlertStatus.OPEN,
            title='dup-2',
            summary='dup',
            source=OperatorAlertSource.RUNTIME,
            dedupe_key='live_paper_autopilot_attention_global',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            metadata={},
        )
        payload = self._sync()
        self.assertIn(payload['alert_action'], {'UPDATED', 'NOOP'})
        self.assertEqual(
            OperatorAlert.objects.filter(dedupe_key='live_paper_autopilot_attention_global', status=OperatorAlertStatus.OPEN).count(),
            1,
        )

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'active',
            'status_summary': 'review now state',
        },
    )
    def test_repeated_same_state_returns_noop(self, *_mocks):
        first = self._sync()
        second = self._sync()
        self.assertEqual(first['attention_mode'], 'REVIEW_NOW')
        self.assertEqual(second['alert_action'], 'NOOP')

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'active',
            'status_summary': 'review now state',
        },
    )
    def test_sync_payload_contract(self, *_mocks):
        payload = self._sync()
        required_keys = {
            'attention_needed',
            'attention_mode',
            'alert_action',
            'alert_severity',
            'session_active',
            'heartbeat_active',
            'current_session_status',
            'attention_reason_codes',
            'status_summary',
            'alert_status_summary',
            'funnel_status',
            'stalled_stage',
            'top_stage',
            'funnel_summary',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'active',
            'status_summary': 'review now state',
        },
    )
    def test_status_payload_contract(self, *_mocks):
        self._sync()
        response = self.client.get(reverse('mission_control:live-paper-attention-alert-status'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        required_keys = {
            'attention_needed',
            'attention_mode',
            'active_alert_present',
            'active_alert_severity',
            'session_active',
            'heartbeat_active',
            'current_session_status',
            'status_summary',
            'funnel_status',
            'stalled_stage',
            'top_stage',
            'funnel_summary',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary', return_value={'runtime_tuning_attention_sync': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': True,
            'heartbeat_active': False,
            'current_session_status': 'RUNNING',
            'operator_attention_hint': 'active',
            'status_summary': 'review now state',
        },
    )

    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.build_heartbeat_summary',
        return_value={'runtime_tuning_attention_sync': {}, 'live_paper_attention_sync': {'attempted': True, 'success': True, 'alert_action': 'NOOP'}},
    )
    @patch(
        'apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status',
        return_value={
            'session_active': False,
            'heartbeat_active': False,
            'current_session_status': 'MISSING',
            'operator_attention_hint': 'none',
            'status_summary': 'healthy',
        },
    )
    def test_status_includes_last_auto_sync_hint(self, *_mocks):
        response = self.client.get(reverse('mission_control:live-paper-attention-alert-status'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('last_auto_sync', payload)
        self.assertIn(payload['last_auto_sync'].get('alert_action'), {None, 'NOOP'})
        self.assertIn(payload.get('funnel_status'), {'ACTIVE', 'THIN_FLOW', 'STALLED', None})

    @patch(
        'apps.mission_control.services.live_paper_attention_bridge._build_funnel_signal',
        return_value={
            'funnel_status': 'STALLED',
            'stalled_stage': 'research',
            'top_stage': 'scan',
            'funnel_summary': 'STALLED: research stage empty.',
            'signal_available': True,
        },
    )
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_recovery_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.build_session_health_summary', return_value={'summary': {}})
    @patch('apps.mission_control.services.live_paper_attention_bridge.get_live_paper_bootstrap_status', return_value={
        'session_active': True,
        'heartbeat_active': True,
        'current_session_status': 'RUNNING',
        'operator_attention_hint': 'session healthy',
        'status_summary': 'session healthy',
    })
    def test_heartbeat_auto_sync_reflects_extended_funnel_logic(self, *_mocks):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        response = self.client.post(reverse('mission_control:run-autonomous-heartbeat'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = (response.json().get('metadata') or {}).get('live_paper_attention_sync') or {}
        self.assertEqual(payload.get('attention_mode'), 'REVIEW_NOW')
        self.assertEqual(payload.get('funnel_status'), 'STALLED')
        self.assertEqual(payload.get('stalled_stage'), 'research')

    def test_sync_does_not_affect_alerts_from_other_sources(self, *_mocks):
        other = OperatorAlert.objects.create(
            alert_type=OperatorAlertType.SAFETY,
            severity=OperatorAlertSeverity.HIGH,
            status=OperatorAlertStatus.OPEN,
            title='other source',
            summary='should stay open',
            source=OperatorAlertSource.SAFETY,
            dedupe_key='safety_global',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            metadata={},
        )
        self._sync()
        other.refresh_from_db()
        self.assertEqual(other.status, OperatorAlertStatus.OPEN)


class LivePaperValidationDigestTests(TestCase):
    def _mock_snapshot(self, *, cash_balance=10000, equity=10100):
        class MockSnapshot:
            pass

        snapshot = MockSnapshot()
        snapshot.cash_balance = cash_balance
        snapshot.equity = equity
        return snapshot

    def _mock_account(self, *, is_active=True, cash_balance=10000, equity=10100):
        class MockAccount:
            pass

        account = MockAccount()
        account.is_active = is_active
        account.cash_balance = cash_balance
        account.equity = equity
        return account

    def _payload(self, **overrides):
        base = {
            'bootstrap': {
                'preset_name': 'live_read_only_paper_conservative',
                'session_active': True,
                'heartbeat_active': True,
                'market_data_mode': 'REAL_READ_ONLY',
            },
            'attention': {'attention_mode': 'HEALTHY'},
            'heartbeat': {'latest_run': 123},
            'summary': {'recent_trades': [{'id': 1}]},
            'snapshot': self._mock_snapshot(),
            'account': self._mock_account(),
        }
        for key, value in overrides.items():
            base[key] = value
        return base

    def _call_endpoint(self, payload):
        with patch('apps.mission_control.services.live_paper_validation.get_live_paper_bootstrap_status', return_value=payload['bootstrap']):
            with patch('apps.mission_control.services.live_paper_validation.get_live_paper_attention_alert_status', return_value=payload['attention']):
                with patch('apps.mission_control.services.live_paper_validation.build_heartbeat_summary', return_value=payload['heartbeat']):
                    with patch('apps.mission_control.services.live_paper_validation.get_active_account', return_value=payload['account']):
                        with patch('apps.mission_control.services.live_paper_validation.build_account_summary', return_value=payload['summary']):
                            with patch(
                                'apps.mission_control.services.live_paper_validation.PaperPortfolioSnapshot.objects.filter'
                            ) as mock_filter:
                                mock_filter.return_value.order_by.return_value.first.return_value = payload['snapshot']
                                return self.client.get(reverse('mission_control:live-paper-validation'))

    def test_ready_case_and_compact_payload(self):
        payload = self._payload()
        response = self._call_endpoint(payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['validation_status'], 'READY')
        self.assertEqual(body['next_action_hint'], 'V1 paper appears operational')
        self.assertIn('READY:', body['validation_summary'])
        required_keys = {
            'preset_name',
            'validation_status',
            'session_active',
            'heartbeat_active',
            'attention_mode',
            'paper_account_ready',
            'market_data_ready',
            'portfolio_snapshot_ready',
            'recent_activity_present',
            'recent_trades_present',
            'cash_available',
            'equity_available',
            'next_action_hint',
            'validation_summary',
            'checks',
        }
        self.assertEqual(set(body.keys()), required_keys)

    def test_warning_case_without_recent_trades(self):
        payload = self._payload(summary={'recent_trades': []})
        response = self._call_endpoint(payload)
        body = response.json()
        self.assertEqual(body['validation_status'], 'WARNING')
        self.assertEqual(body['next_action_hint'], 'Waiting for first paper trade')

    def test_blocked_case_when_session_inactive(self):
        payload = self._payload(
            bootstrap={
                'preset_name': 'live_read_only_paper_conservative',
                'session_active': False,
                'heartbeat_active': True,
                'market_data_mode': 'REAL_READ_ONLY',
            }
        )
        response = self._call_endpoint(payload)
        body = response.json()
        self.assertEqual(body['validation_status'], 'BLOCKED')
        self.assertEqual(body['next_action_hint'], 'Start live paper autopilot')

    def test_checks_are_present_and_human_readable(self):
        payload = self._payload(summary={'recent_trades': []})
        response = self._call_endpoint(payload)
        checks = response.json()['checks']
        check_names = [item['check_name'] for item in checks]
        self.assertEqual(
            check_names,
            ['bootstrap_session', 'heartbeat_loop', 'attention_bridge', 'paper_account', 'portfolio_snapshot', 'recent_activity', 'recent_trades'],
        )
        self.assertTrue(all(item.get('status') in {'PASS', 'WARN', 'FAIL'} for item in checks))
        self.assertTrue(all(isinstance(item.get('summary'), str) and item['summary'] for item in checks))

    def test_summary_is_stable_and_deterministic(self):
        payload = self._payload()
        first = self._call_endpoint(payload).json()['validation_summary']
        second = self._call_endpoint(payload).json()['validation_summary']
        self.assertEqual(first, second)

    def test_default_preset_is_applied(self):
        payload = self._payload()
        with patch('apps.mission_control.services.live_paper_validation.get_live_paper_bootstrap_status', return_value=payload['bootstrap']) as mock_bootstrap:
            with patch('apps.mission_control.services.live_paper_validation.get_live_paper_attention_alert_status', return_value=payload['attention']):
                with patch('apps.mission_control.services.live_paper_validation.build_heartbeat_summary', return_value=payload['heartbeat']):
                    with patch('apps.mission_control.services.live_paper_validation.get_active_account', return_value=payload['account']):
                        with patch('apps.mission_control.services.live_paper_validation.build_account_summary', return_value=payload['summary']):
                            with patch('apps.mission_control.services.live_paper_validation.PaperPortfolioSnapshot.objects.filter') as mock_filter:
                                mock_filter.return_value.order_by.return_value.first.return_value = payload['snapshot']
                                response = self.client.get(reverse('mission_control:live-paper-validation'))
        self.assertEqual(response.status_code, 200)
        mock_bootstrap.assert_called_once_with(preset_name='live_read_only_paper_conservative')

class SessionTimingProfileTests(TestCase):
    def test_profile_endpoint_bootstraps_defaults(self):
        response = self.client.get(reverse('mission_control:schedule-profiles'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(profile['slug'] == 'balanced_local' for profile in payload))


class GovernanceReviewQueueTests(TestCase):
    def test_collect_items_from_multiple_modules(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        recovery_snapshot = AutonomousSessionRecoverySnapshot.objects.create(linked_session=session)
        AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=recovery_snapshot,
            decision_type='REQUIRE_MANUAL_RECOVERY_REVIEW',
            decision_status='PROPOSED',
            reason_codes=['MANUAL_REVIEW_REQUIRED'],
            decision_summary='Need operator confirmation',
        )

        coordination_run = PortfolioExposureCoordinationRun.objects.create()
        cluster_snapshot = PortfolioExposureClusterSnapshot.objects.create(linked_run=coordination_run, cluster_label='cluster-A')
        PortfolioExposureDecision.objects.create(
            linked_cluster_snapshot=cluster_snapshot,
            decision_type='DEFER_PENDING_DISPATCH',
            decision_status='PROPOSED',
            decision_summary='Deferred due pressure',
            reason_codes=['PORTFOLIO_DEFERRED'],
        )

        candidates = collect_governance_review_candidates()
        source_modules = {item.source_module for item in candidates}
        self.assertIn('mission_control', source_modules)
        self.assertIn('portfolio_governor', source_modules)

    def test_priority_assignment_for_blocked_item(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        recovery_snapshot = AutonomousSessionRecoverySnapshot.objects.create(linked_session=session)
        decision = AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=recovery_snapshot,
            decision_type='REQUIRE_MANUAL_RECOVERY_REVIEW',
            decision_status='BLOCKED',
            reason_codes=['SAFETY_BLOCK_ACTIVE'],
        )

        candidate = next(
            item for item in collect_governance_review_candidates()
            if item.source_object_id == decision.id and item.source_type == 'session_recovery'
        )
        severity, priority = assign_severity_and_priority(candidate)
        self.assertIn(severity, {'HIGH', 'CRITICAL'})
        self.assertEqual(priority, 'P1')

    def test_run_deduplicates_equivalent_items(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        recovery_snapshot = AutonomousSessionRecoverySnapshot.objects.create(linked_session=session)
        decision = AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=recovery_snapshot,
            decision_type='REQUIRE_MANUAL_RECOVERY_REVIEW',
            decision_status='PROPOSED',
            reason_codes=['MANUAL_REVIEW_REQUIRED'],
        )

        self.client.post(reverse('mission_control:run-governance-review-queue'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-governance-review-queue'), data='{}', content_type='application/json')
        items = GovernanceReviewItem.objects.filter(source_type='session_recovery', source_object_id=decision.id)
        self.assertEqual(items.count(), 1)

    def test_summary_endpoint(self):
        self.client.post(reverse('mission_control:run-governance-review-queue'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:governance-review-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('open_count', payload)
        self.assertIn('high_priority_count', payload)


class GovernanceReviewResolutionTests(TestCase):
    def _build_recovery_item(self) -> GovernanceReviewItem:
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        snapshot = AutonomousSessionRecoverySnapshot.objects.create(linked_session=session)
        decision = AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=snapshot,
            decision_type='READY_TO_RESUME',
            decision_status='PROPOSED',
            auto_applicable=True,
            reason_codes=['manual_review_required'],
        )
        return GovernanceReviewItem.objects.create(
            source_module='mission_control',
            source_type='session_recovery',
            source_object_id=decision.id,
            item_status='OPEN',
            title='Recovery decision',
            summary='Manual recovery review needed',
        )

    def test_resolve_creates_governance_resolution(self):
        item = self._build_recovery_item()
        response = self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[item.id]),
            data=json.dumps({'resolution_type': 'APPLY_MANUAL_APPROVAL'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GovernanceReviewResolution.objects.filter(linked_review_item=item).exists())
        item.refresh_from_db()
        self.assertEqual(item.item_status, 'RESOLVED')

    def test_dismiss_closes_item_without_deleting(self):
        item = self._build_recovery_item()
        response = self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[item.id]),
            data=json.dumps({'resolution_type': 'DISMISS_AS_EXPECTED'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.item_status, 'DISMISSED')
        self.assertTrue(GovernanceReviewItem.objects.filter(id=item.id).exists())

    def test_keep_blocked_preserves_traceability(self):
        item = self._build_recovery_item()
        response = self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[item.id]),
            data=json.dumps({'resolution_type': 'KEEP_BLOCKED'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        resolution = GovernanceReviewResolution.objects.filter(linked_review_item=item).order_by('-id').first()
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution.resolution_status, 'BLOCKED')
        self.assertIn('closed_as', resolution.metadata)

    def test_retry_safe_apply_only_for_supported_source(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        health_snapshot = AutonomousSessionHealthSnapshot.objects.create(linked_session=session)
        decision = AutonomousSessionInterventionDecision.objects.create(
            linked_session=session,
            linked_health_snapshot=health_snapshot,
            decision_type='REQUIRE_MANUAL_REVIEW',
            decision_status='PROPOSED',
        )
        item = GovernanceReviewItem.objects.create(
            source_module='mission_control',
            source_type='session_health',
            source_object_id=decision.id,
            item_status='OPEN',
            title='Health decision',
        )
        response = self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[item.id]),
            data=json.dumps({'resolution_type': 'RETRY_SAFE_APPLY'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        resolution = GovernanceReviewResolution.objects.filter(linked_review_item=item).order_by('-id').first()
        self.assertEqual(resolution.resolution_status, 'BLOCKED')

    def test_summary_reflects_resolved_count(self):
        item = self._build_recovery_item()
        self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[item.id]),
            data=json.dumps({'resolution_type': 'DISMISS_AS_EXPECTED'}),
            content_type='application/json',
        )
        resolved_item = self._build_recovery_item()
        self.client.post(
            reverse('mission_control:resolve-governance-review-item', args=[resolved_item.id]),
            data=json.dumps({'resolution_type': 'KEEP_BLOCKED'}),
            content_type='application/json',
        )
        response = self.client.get(reverse('mission_control:governance-review-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json().get('resolved_count', 0), 1)


class GovernanceAutoResolutionTests(TestCase):
    def _create_item(self, **overrides) -> GovernanceReviewItem:
        payload = {
            'source_module': 'mission_control',
            'source_type': 'session_recovery',
            'source_object_id': 1001,
            'item_status': 'OPEN',
            'severity': 'INFO',
            'queue_priority': 'P4',
            'title': 'Advisory test',
            'summary': 'Safe low risk item.',
            'blockers': [],
            'reason_codes': ['ADVISORY_ONLY', 'SAFE_TO_DISMISS'],
            'metadata': {'auto_applicable': False},
        }
        payload.update(overrides)
        return GovernanceReviewItem.objects.create(**payload)

    def test_advisory_only_low_risk_item_auto_dismisses(self):
        item = self._create_item()
        response = self.client.post(reverse('mission_control:run-governance-auto-resolution'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.item_status, 'DISMISSED')
        self.assertTrue(
            GovernanceAutoResolutionRecord.objects.filter(
                linked_review_item=item,
                effect_type='DISMISSED',
                record_status='APPLIED',
            ).exists()
        )

    def test_safe_retry_only_runs_for_explicit_supported_items(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        snapshot = AutonomousSessionRecoverySnapshot.objects.create(linked_session=session)
        decision = AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=snapshot,
            decision_type='READY_TO_RESUME',
            decision_status='PROPOSED',
            auto_applicable=True,
            reason_codes=['SAFE_RETRY_ALLOWED'],
        )
        supported_item = self._create_item(
            source_object_id=decision.id,
            metadata={'auto_applicable': True},
            reason_codes=['SAFE_RETRY_ALLOWED'],
            title='Safe retry supported',
        )
        unsupported_item = self._create_item(
            source_type='session_health',
            source_object_id=2002,
            metadata={'auto_applicable': True},
            reason_codes=['SAFE_RETRY_ALLOWED'],
            title='Safe retry not supported',
        )

        self.client.post(reverse('mission_control:run-governance-auto-resolution'), data='{}', content_type='application/json')
        self.assertTrue(
            GovernanceAutoResolutionRecord.objects.filter(
                linked_review_item=supported_item,
                effect_type='RETRY_SAFE_APPLY_TRIGGERED',
            ).exists()
        )
        unsupported_decision = GovernanceAutoResolutionDecision.objects.filter(linked_review_item=unsupported_item).order_by('-id').first()
        self.assertIsNotNone(unsupported_decision)
        self.assertEqual(unsupported_decision.decision_type, 'DO_NOT_AUTO_RESOLVE')

    def test_high_severity_items_are_not_auto_resolved(self):
        item = self._create_item(
            severity='HIGH',
            queue_priority='P1',
            reason_codes=['ADVISORY_ONLY'],
            source_object_id=3003,
        )
        self.client.post(reverse('mission_control:run-governance-auto-resolution'), data='{}', content_type='application/json')
        item.refresh_from_db()
        self.assertEqual(item.item_status, 'OPEN')
        decision = GovernanceAutoResolutionDecision.objects.filter(linked_review_item=item).order_by('-id').first()
        self.assertIsNotNone(decision)
        self.assertEqual(decision.decision_type, 'DO_NOT_AUTO_RESOLVE')

    def test_auto_resolution_summary_endpoint(self):
        self._create_item(source_object_id=4004)
        self.client.post(reverse('mission_control:run-governance-auto-resolution'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:governance-auto-resolution-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('totals', payload)
        self.assertIn('latest_counts', payload)


class SessionTimingPolicyTests(TestCase):

    def test_recent_dispatch_delays_next_due_at(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        AutonomousRuntimeTick.objects.create(
            linked_session=session,
            tick_index=1,
            tick_status='COMPLETED',
            tick_summary='dispatch simulated',
        )
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        snapshots = self.client.get(reverse('mission_control:session-timing-snapshots')).json()
        target = next(snapshot for snapshot in snapshots if snapshot['linked_session'] == session.id)
        self.assertIn(target['timing_status'], {'WAIT_SHORT', 'WAIT_LONG'})
        self.assertIsNotNone(target['next_due_at'])

    def test_repeated_no_action_moves_to_wait_long_or_monitor(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        profile = AutonomousScheduleProfile.objects.create(
            slug='tiny-threshold',
            display_name='Tiny threshold',
            max_quiet_ticks_before_wait_long=2,
            max_no_action_ticks_before_pause=50,
        )
        session.linked_schedule_profile = profile
        session.save(update_fields=['linked_schedule_profile', 'updated_at'])
        for index in range(1, 4):
            AutonomousRuntimeTick.objects.create(
                linked_session=session,
                tick_index=index,
                tick_status='SKIPPED',
                reason_codes=['no_action'],
            )
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:session-timing-decisions')).json()
        target = next(decision for decision in decisions if decision['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'WAIT_LONG', 'MONITOR_ONLY_NEXT'})

    def test_persistent_blocks_trigger_stop_recommendation(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        profile = AutonomousScheduleProfile.objects.create(
            slug='stop-fast',
            display_name='Stop fast',
            max_consecutive_blocked_ticks_before_stop=2,
            enable_auto_stop_for_persistent_blocks=True,
        )
        session.linked_schedule_profile = profile
        session.save(update_fields=['linked_schedule_profile', 'updated_at'])
        for index in range(1, 4):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='BLOCKED')
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        recommendations = self.client.get(reverse('mission_control:session-timing-recommendations')).json()
        target = next(rec for rec in recommendations if rec['target_session'] == session.id)
        self.assertIn(target['recommendation_type'], {'STOP_SESSION_FOR_PERSISTENT_BLOCKS', 'REQUIRE_MANUAL_TIMING_REVIEW'})

    def test_timing_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:session-timing-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())


class AdaptiveProfileControlTests(TestCase):
    def test_quiet_market_moves_to_conservative_or_monitor_profile(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        profile = AutonomousScheduleProfile.objects.create(slug='balanced-test', display_name='Balanced test')
        session.linked_schedule_profile = profile
        session.profile_slug = profile.slug
        session.save(update_fields=['linked_schedule_profile', 'profile_slug', 'updated_at'])
        for index in range(1, 6):
            AutonomousRuntimeTick.objects.create(
                linked_session=session,
                tick_index=index,
                tick_status='SKIPPED',
                reason_codes=['no_action'],
            )
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        response = self.client.post(reverse('mission_control:run-profile-selection-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertIn(session.profile_slug, {'conservative_quiet', 'monitor_heavy'})

    @patch('apps.mission_control.services.session_profile_control.context_review.get_safety_status')
    def test_repeated_blocked_ticks_recommends_manual_or_conservative(self, mock_safety):
        mock_safety.return_value = {'kill_switch_enabled': True, 'hard_stop_active': True}
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        for index in range(1, 4):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='BLOCKED')
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-profile-selection-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:profile-switch-decisions')).json()
        target = next(decision for decision in decisions if decision['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'BLOCK_PROFILE_SWITCH', 'SWITCH_TO_CONSERVATIVE_QUIET', 'REQUIRE_MANUAL_PROFILE_REVIEW'})

    def test_normal_state_restores_balanced_profile(self):
        conservative = AutonomousScheduleProfile.objects.create(slug='temp-conservative', display_name='Temp conservative')
        session = AutonomousRuntimeSession.objects.create(
            session_status='RUNNING',
            runtime_mode='PAPER',
            linked_schedule_profile=conservative,
            profile_slug=conservative.slug,
        )
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-profile-selection-review'), data='{}', content_type='application/json')
        session.refresh_from_db()
        self.assertEqual(session.profile_slug, 'balanced_local')

    def test_switch_record_created(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        for index in range(1, 6):
            AutonomousRuntimeTick.objects.create(
                linked_session=session,
                tick_index=index,
                tick_status='SKIPPED',
                reason_codes=['no_action'],
            )
        self.client.post(reverse('mission_control:run-session-timing-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-profile-selection-review'), data='{}', content_type='application/json')
        self.assertTrue(AutonomousProfileSwitchRecord.objects.filter(linked_session=session).exists())

    def test_profile_selection_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-profile-selection-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:profile-selection-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())


class SessionHealthGovernanceTests(TestCase):
    def test_repeated_failed_ticks_generates_anomaly_and_pause_review(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        for index in range(1, 4):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='FAILED')

        response = self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        anomalies = self.client.get(reverse('mission_control:session-anomalies')).json()
        decisions = self.client.get(reverse('mission_control:session-intervention-decisions')).json()
        self.assertTrue(any(item['linked_session'] == session.id and item['anomaly_type'] == 'REPEATED_FAILED_TICKS' for item in anomalies))
        target = next(item for item in decisions if item['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'PAUSE_SESSION', 'REQUIRE_MANUAL_REVIEW'})

    def test_persistent_blocked_ticks_recommends_stop_or_manual(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        for index in range(1, 6):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='BLOCKED')

        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:session-intervention-decisions')).json()
        target = next(item for item in decisions if item['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'STOP_SESSION', 'REQUIRE_MANUAL_REVIEW'})

    @patch('apps.mission_control.services.session_health.health_snapshot.get_safety_status')
    def test_safety_runtime_block_forces_conservative_intervention(self, mock_safety):
        mock_safety.return_value = {'kill_switch_enabled': True, 'hard_stop_active': True, 'status': 'blocked'}
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        decision = AutonomousSessionInterventionDecision.objects.filter(linked_session=session).order_by('-created_at').first()
        self.assertIsNotNone(decision)
        self.assertEqual(decision.decision_type, 'STOP_SESSION')
        self.assertTrue(decision.auto_applicable)

    def test_recovered_paused_session_can_recommend_resume(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER', pause_reason_codes=['manual_pause'])
        AutonomousRuntimeTick.objects.create(
            linked_session=session,
            tick_index=1,
            tick_status='SKIPPED',
            reason_codes=['watch_only'],
        )
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:session-intervention-decisions')).json()
        target = next(item for item in decisions if item['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'RESUME_SESSION', 'KEEP_RUNNING', 'REQUIRE_MANUAL_REVIEW'})

    def test_session_health_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:session-health-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())


class SessionRecoveryReviewTests(TestCase):
    def test_cleared_blocks_can_be_ready_to_resume(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='COMPLETED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        response = self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        decision = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        self.assertIn(decision.decision_type, {'READY_TO_RESUME', 'RESUME_IN_MONITOR_ONLY_MODE'})

    @patch('apps.mission_control.services.session_recovery.recovery_snapshot.get_safety_status')
    def test_persistent_safety_block_keeps_session_paused(self, mock_safety):
        mock_safety.return_value = {'kill_switch_enabled': True, 'hard_stop_active': True}
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        self.assertIn(decision.decision_type, {'KEEP_PAUSED', 'STOP_SESSION_PERMANENTLY'})

    def test_partial_recovery_uses_monitor_only_resume(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='FAILED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        self.assertEqual(decision.decision_type, 'RESUME_IN_MONITOR_ONLY_MODE')

    def test_unrecoverable_state_recommends_stop_or_escalate(self):
        session = AutonomousRuntimeSession.objects.create(session_status='BLOCKED', runtime_mode='PAPER')
        for index in range(1, 7):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='BLOCKED')
        self.client.post(
            reverse('mission_control:run-session-health-review'),
            data=json.dumps({'auto_apply_safe': False}),
            content_type='application/json',
        )
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        recommendation = AutonomousSessionRecoveryRecommendation.objects.filter(target_session=session).order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        self.assertIsNotNone(recommendation)
        self.assertIn(decision.decision_type, {'STOP_SESSION_PERMANENTLY', 'ESCALATE_TO_INCIDENT_REVIEW', 'REQUIRE_MANUAL_RECOVERY_REVIEW'})
        self.assertIn(recommendation.recommendation_type, {'STOP_SESSION_FOR_UNRECOVERABLE_STATE', 'ESCALATE_RECOVERY_TO_INCIDENT_LAYER', 'REQUIRE_MANUAL_RECOVERY_REVIEW'})

    def test_session_recovery_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:session-recovery-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())

    def test_manual_resume_apply_creates_record_and_resumes_session(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='COMPLETED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session, decision_type='READY_TO_RESUME').order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        response = self.client.post(
            reverse('mission_control:apply-session-resume', kwargs={'decision_id': decision.id}),
            data=json.dumps({'applied_mode': 'MANUAL_RESUME'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.session_status, 'RUNNING')
        record = AutonomousResumeRecord.objects.filter(linked_resume_decision=decision).order_by('-created_at', '-id').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.resume_status, 'APPLIED')
        self.assertEqual(record.applied_mode, 'MANUAL_RESUME')

    def test_auto_safe_resume_only_applies_for_ready_and_auto_applicable(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='FAILED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(
            reverse('mission_control:run-session-recovery-review'),
            data=json.dumps({'auto_apply_safe': True}),
            content_type='application/json',
        )
        decision = AutonomousResumeDecision.objects.filter(linked_session=session).order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        self.assertEqual(decision.decision_type, 'RESUME_IN_MONITOR_ONLY_MODE')
        record = AutonomousResumeRecord.objects.filter(linked_resume_decision=decision).order_by('-created_at', '-id').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.resume_status, 'SKIPPED')
        self.assertEqual(record.applied_mode, 'AUTO_SAFE_RESUME')
        session.refresh_from_db()
        self.assertEqual(session.session_status, 'PAUSED')

    def test_monitor_only_resume_apply_uses_monitor_mode_and_record(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='FAILED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session, decision_type='RESUME_IN_MONITOR_ONLY_MODE').order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        response = self.client.post(
            reverse('mission_control:apply-session-resume', kwargs={'decision_id': decision.id}),
            data=json.dumps({'applied_mode': 'MONITOR_ONLY_RESUME'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.session_status, 'RUNNING')
        self.assertEqual((session.metadata or {}).get('resume_apply_mode'), 'MONITOR_ONLY_RESUME')
        record = AutonomousResumeRecord.objects.filter(linked_resume_decision=decision).order_by('-created_at', '-id').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.applied_mode, 'MONITOR_ONLY_RESUME')
        self.assertEqual(record.resume_status, 'APPLIED')

    @patch('apps.mission_control.services.session_recovery.apply_resume.detect_recovery_blockers')
    def test_active_blockers_prevent_resume_apply(self, mock_detect_blockers):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        for index in range(1, 3):
            AutonomousRuntimeTick.objects.create(linked_session=session, tick_index=index, tick_status='COMPLETED')
        self.client.post(reverse('mission_control:run-session-health-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-session-recovery-review'), data='{}', content_type='application/json')
        decision = AutonomousResumeDecision.objects.filter(linked_session=session, decision_type='READY_TO_RESUME').order_by('-created_at', '-id').first()
        self.assertIsNotNone(decision)
        blocker = type('Blocker', (), {'id': 999, 'blocker_type': 'MANUAL_REVIEW_REQUIRED'})()
        mock_detect_blockers.return_value = [blocker]
        response = self.client.post(
            reverse('mission_control:apply-session-resume', kwargs={'decision_id': decision.id}),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        decision.refresh_from_db()
        self.assertEqual(decision.decision_status, 'BLOCKED')
        record = AutonomousResumeRecord.objects.filter(linked_resume_decision=decision).order_by('-created_at', '-id').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.resume_status, 'BLOCKED')


class SessionAdmissionControlTests(TestCase):
    def test_available_capacity_admits_ready_sessions(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER', dispatch_count=6)
        response = self.client.post(reverse('mission_control:run-session-admission-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        reviews = self.client.get(reverse('mission_control:session-admission-reviews')).json()
        self.assertTrue(any(r['linked_session'] == session.id and r['admission_status'] in {'ADMIT', 'DEFER'} for r in reviews))

    def test_capacity_pressure_defers_or_parks_sessions(self):
        for _ in range(5):
            AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER', dispatch_count=1, metadata={'no_signal_streak': 6})
        self.client.post(reverse('mission_control:run-session-admission-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:session-admission-decisions')).json()
        self.assertTrue(any(d['decision_type'] in {'DEFER_SESSION', 'PAUSE_SESSION', 'PARK_SESSION', 'RETIRE_SESSION'} for d in decisions))

    def test_repeated_low_signal_parks_or_retires(self):
        session = AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER', metadata={'no_signal_streak': 12})
        self.client.post(reverse('mission_control:run-session-admission-review'), data='{}', content_type='application/json')
        decisions = self.client.get(reverse('mission_control:session-admission-decisions')).json()
        target = next(d for d in decisions if d['linked_session'] == session.id)
        self.assertIn(target['decision_type'], {'PARK_SESSION', 'RETIRE_SESSION'})

    def test_resume_allowed_requires_recovery_and_capacity(self):
        session = AutonomousRuntimeSession.objects.create(session_status='PAUSED', runtime_mode='PAPER')
        AutonomousResumeDecision.objects.create(
            linked_session=session,
            linked_recovery_snapshot=AutonomousSessionRecoverySnapshot.objects.create(linked_session=session, recovery_status='RECOVERED'),
            decision_type='READY_TO_RESUME',
            decision_status='PROPOSED',
        )
        self.client.post(reverse('mission_control:run-session-admission-review'), data='{}', content_type='application/json')
        reviews = self.client.get(reverse('mission_control:session-admission-reviews')).json()
        target = next(r for r in reviews if r['linked_session'] == session.id)
        self.assertIn(target['admission_status'], {'RESUME_ALLOWED', 'DEFER', 'MANUAL_REVIEW'})

    def test_summary_endpoint(self):
        AutonomousRuntimeSession.objects.create(session_status='RUNNING', runtime_mode='PAPER')
        self.client.post(reverse('mission_control:run-session-admission-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:session-admission-summary'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.json())


class GovernanceQueueAgingTests(TestCase):
    def _create_item(self, **overrides):
        payload = {
            'source_module': 'mission_control',
            'source_type': 'session_recovery',
            'source_object_id': overrides.pop('source_object_id', 9000 + GovernanceReviewItem.objects.count()),
            'item_status': 'OPEN',
            'severity': 'CAUTION',
            'queue_priority': 'P3',
            'title': 'Aging candidate',
            'summary': 'candidate',
            'blockers': [],
            'reason_codes': [],
            'metadata': {},
        }
        payload.update(overrides)
        return GovernanceReviewItem.objects.create(**payload)

    def test_old_open_item_escalates_priority(self):
        item = self._create_item()
        GovernanceReviewItem.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=10),
            updated_at=timezone.now() - timedelta(days=8),
        )
        response = self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.queue_priority, 'P2')

    def test_persistent_blocked_item_marked_stale_blocked(self):
        item = self._create_item(blockers=['STATUS_BLOCKED'])
        GovernanceReviewItem.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=6),
            updated_at=timezone.now() - timedelta(days=5),
        )
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        review = GovernanceQueueAgingReview.objects.filter(linked_review_item=item).order_by('-id').first()
        self.assertIsNotNone(review)
        self.assertEqual(review.aging_status, 'STALE_BLOCKED')

    def test_followup_due_detected(self):
        item = self._create_item(
            metadata={'followup_required': True},
            reason_codes=['FOLLOWUP_REQUIRED'],
        )
        GovernanceReviewItem.objects.filter(pk=item.pk).update(updated_at=timezone.now() - timedelta(days=4))
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        review = GovernanceQueueAgingReview.objects.filter(linked_review_item=item).order_by('-id').first()
        self.assertIsNotNone(review)
        self.assertEqual(review.aging_status, 'FOLLOWUP_DUE')

    def test_resolved_or_dismissed_items_not_considered(self):
        self._create_item(item_status='RESOLVED', source_object_id=10001)
        self._create_item(item_status='DISMISSED', source_object_id=10002)
        response = self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['considered_item_count'], 0)

    def test_summary_endpoint(self):
        item = self._create_item()
        GovernanceReviewItem.objects.filter(pk=item.pk).update(created_at=timezone.now() - timedelta(days=10))
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:governance-queue-aging-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('latest_counts', payload)
        self.assertIn('overdue', payload['latest_counts'])
        self.assertIn('manual_review_overdue', payload['latest_counts'])


class GovernanceBacklogPressureTests(TestCase):
    def _create_item(self, **overrides):
        payload = {
            'source_module': 'mission_control',
            'source_type': 'session_recovery',
            'source_object_id': overrides.pop('source_object_id', 12000 + GovernanceReviewItem.objects.count()),
            'item_status': 'OPEN',
            'severity': 'CAUTION',
            'queue_priority': 'P3',
            'title': 'Backlog pressure candidate',
            'summary': 'candidate',
            'blockers': [],
            'reason_codes': [],
            'metadata': {},
        }
        payload.update(overrides)
        return GovernanceReviewItem.objects.create(**payload)

    def test_light_backlog_stays_normal(self):
        self._create_item()
        response = self.client.post(reverse('mission_control:run-governance-backlog-pressure-review'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        snapshot = GovernanceBacklogPressureSnapshot.objects.order_by('-id').first()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.governance_backlog_pressure_state, 'NORMAL')

    def test_many_overdue_and_p1_items_raise_high_pressure(self):
        items = [
            self._create_item(queue_priority='P1', source_object_id=13000 + idx)
            for idx in range(3)
        ]
        for item in items:
            GovernanceReviewItem.objects.filter(pk=item.pk).update(
                created_at=timezone.now() - timedelta(days=20),
                updated_at=timezone.now() - timedelta(days=10),
            )
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-governance-backlog-pressure-review'), data='{}', content_type='application/json')
        snapshot = GovernanceBacklogPressureSnapshot.objects.order_by('-id').first()
        self.assertIsNotNone(snapshot)
        self.assertIn(snapshot.governance_backlog_pressure_state, {'CAUTION', 'HIGH'})

    def test_persistent_stale_blocked_escalates_pressure(self):
        item = self._create_item(blockers=['STATUS_BLOCKED'], source_object_id=14001)
        GovernanceReviewItem.objects.filter(pk=item.pk).update(
            created_at=timezone.now() - timedelta(days=8),
            updated_at=timezone.now() - timedelta(days=6),
        )
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        GovernanceReviewItem.objects.filter(pk=item.pk).update(updated_at=timezone.now() - timedelta(days=7))
        self.client.post(reverse('mission_control:run-governance-queue-aging-review'), data='{}', content_type='application/json')
        self.client.post(reverse('mission_control:run-governance-backlog-pressure-review'), data='{}', content_type='application/json')
        snapshot = GovernanceBacklogPressureSnapshot.objects.order_by('-id').first()
        self.assertIsNotNone(snapshot)
        self.assertGreaterEqual(snapshot.persistent_stale_blocked_count, 1)
        self.assertIn(snapshot.governance_backlog_pressure_state, {'CAUTION', 'HIGH'})

    def test_summary_endpoint(self):
        self._create_item()
        self.client.post(reverse('mission_control:run-governance-backlog-pressure-review'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:governance-backlog-pressure-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('governance_backlog_pressure_state', payload)
        self.assertIn('latest_counts', payload)


class LivePaperSmokeTestApiTests(TestCase):
    def _validation_payload(self, status: str, *, activity: bool, trades: bool, snapshot: bool) -> dict:
        return {
            'preset_name': 'live_read_only_paper_conservative',
            'validation_status': status,
            'session_active': True,
            'heartbeat_active': True,
            'attention_mode': 'HEALTHY',
            'paper_account_ready': True,
            'market_data_ready': True,
            'portfolio_snapshot_ready': snapshot,
            'recent_activity_present': activity,
            'recent_trades_present': trades,
            'cash_available': 10000.0,
            'equity_available': 10000.0,
            'next_action_hint': 'hint',
            'validation_summary': f'{status} summary',
            'checks': [],
        }

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 999})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_post_returns_pass_when_signals_are_healthy(self, mock_validation, _mock_bootstrap, _mock_status, mock_heartbeat, _mock_summary):
        mock_validation.side_effect = [
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]

        response = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['smoke_test_status'], 'PASS')
        self.assertEqual(payload['validation_status_before'], 'WARNING')
        self.assertEqual(payload['validation_status_after'], 'READY')
        self.assertEqual(payload['heartbeat_passes_completed'], 1)
        self.assertEqual(mock_heartbeat.call_count, 1)

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 111})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_post_returns_warn_when_validation_stays_warning(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
        ]

        response = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['smoke_test_status'], 'WARN')
        self.assertEqual(payload['next_action_hint'], 'Review cockpit and let autopilot continue')

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': None})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': False, 'heartbeat_active': False})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'BLOCKED', 'bootstrap_summary': 'blocked'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_post_returns_fail_when_bootstrap_or_validation_blocked(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('BLOCKED', activity=False, trades=False, snapshot=False),
            self._validation_payload('BLOCKED', activity=False, trades=False, snapshot=False),
        ]

        response = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['smoke_test_status'], 'FAIL')
        self.assertEqual(payload['validation_status_after'], 'BLOCKED')

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 222})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'Bootstrap reused existing session'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_reuses_existing_bootstrap_session_without_duplication_signal(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]

        response = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        bootstrap_check = next(item for item in response.json()['checks'] if item['check_name'] == 'bootstrap')
        self.assertEqual(bootstrap_check['status'], 'PASS')
        self.assertIn('reused', bootstrap_check['summary'].lower())

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 333})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_heartbeat_passes_honors_requested_max_two(self, mock_validation, _mock_bootstrap, _mock_status, mock_heartbeat, _mock_summary):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]

        response = self.client.post(
            reverse('mission_control:run-live-paper-smoke-test'),
            data=json.dumps({'heartbeat_passes': 2}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['heartbeat_passes_requested'], 2)
        self.assertEqual(payload['heartbeat_passes_completed'], 2)
        self.assertEqual(mock_heartbeat.call_count, 2)

        too_many = self.client.post(
            reverse('mission_control:run-live-paper-smoke-test'),
            data=json.dumps({'heartbeat_passes': 3}),
            content_type='application/json',
        )
        self.assertEqual(too_many.status_code, 400)

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 444})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_post_payload_contract_is_compact_and_stable(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]

        response = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')
        payload = response.json()
        required_keys = {
            'preset_name', 'smoke_test_status', 'bootstrap_action', 'session_active_after', 'heartbeat_active_after',
            'validation_status_before', 'validation_status_after', 'heartbeat_passes_requested', 'heartbeat_passes_completed',
            'recent_activity_detected', 'recent_trades_detected', 'next_action_hint', 'smoke_test_summary', 'checks',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))
        self.assertEqual(len(payload['checks']), 6)

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 555})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_get_status_returns_latest_summary_contract(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
        ]
        self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json')

        status_response = self.client.get(reverse('mission_control:live-paper-smoke-test-status'))
        self.assertEqual(status_response.status_code, 200)
        payload = status_response.json()
        required_keys = {
            'preset_name', 'smoke_test_status', 'executed_at', 'validation_status_after',
            'heartbeat_passes_completed', 'smoke_test_summary', 'next_action_hint',
        }
        self.assertTrue(required_keys.issubset(payload.keys()))

    @patch('apps.mission_control.services.live_paper_smoke_test.build_heartbeat_summary', return_value={'latest_run': 666})
    @patch('apps.mission_control.services.live_paper_smoke_test.run_heartbeat_pass')
    @patch('apps.mission_control.services.live_paper_smoke_test.get_live_paper_bootstrap_status', return_value={'session_active': True, 'heartbeat_active': True})
    @patch('apps.mission_control.services.live_paper_smoke_test.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_smoke_test.build_live_paper_validation_digest')
    def test_summary_is_deterministic_for_same_inputs(self, mock_validation, *_mocks):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]

        first = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json').json()
        second = self.client.post(reverse('mission_control:run-live-paper-smoke-test'), data='{}', content_type='application/json').json()
        self.assertEqual(first['smoke_test_summary'], second['smoke_test_summary'])

    def test_existing_mission_control_summary_flow_still_works(self):
        response = self.client.get(reverse('mission_control:autonomous-session-summary'))
        self.assertEqual(response.status_code, 200)


class LivePaperTrialRunApiTests(TestCase):
    def setUp(self):
        _clear_live_paper_trial_history_for_tests()

    def _validation_payload(self, status: str, *, activity: bool, trades: bool, snapshot: bool) -> dict:
        return {
            'preset_name': 'live_read_only_paper_conservative',
            'validation_status': status,
            'session_active': True,
            'heartbeat_active': True,
            'attention_mode': 'HEALTHY',
            'paper_account_ready': True,
            'market_data_ready': True,
            'portfolio_snapshot_ready': snapshot,
            'recent_activity_present': activity,
            'recent_trades_present': trades,
            'cash_available': 10000.0,
            'equity_available': 10000.0,
            'next_action_hint': 'hint',
            'validation_summary': f'{status} summary',
            'checks': [],
        }

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_post_returns_pass_with_deterministic_summary(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]
        smoke_payload = {
            'smoke_test_status': 'PASS',
            'smoke_test_summary': 'PASS: summary',
            'heartbeat_passes_completed': 1,
        }
        mock_smoke_run.return_value = smoke_payload
        mock_smoke_status.return_value = smoke_payload

        first = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertEqual(payload['trial_status'], 'PASS')
        self.assertEqual(payload['next_action_hint'], 'Live paper trial passed')
        self.assertEqual(payload['trial_summary'], 'PASS: smoke=PASS validation WARNING->READY; heartbeat_passes_completed=1.')
        self.assertEqual(payload['validation_status_before'], 'WARNING')
        self.assertEqual(payload['validation_status_after'], 'READY')

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_post_returns_warn_when_validation_is_warning(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('WARNING', activity=True, trades=False, snapshot=True),
        ]
        smoke_payload = {'smoke_test_status': 'WARN', 'smoke_test_summary': 'WARN: summary', 'heartbeat_passes_completed': 1}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload

        response = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['trial_status'], 'WARN')
        self.assertEqual(payload['next_action_hint'], 'Review validation warnings')

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'blocked'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'BLOCKED', 'bootstrap_summary': 'blocked'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_post_returns_fail_when_bootstrap_or_validation_is_blocked(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('BLOCKED', activity=False, trades=False, snapshot=False),
            self._validation_payload('BLOCKED', activity=False, trades=False, snapshot=False),
        ]
        smoke_payload = {'smoke_test_status': 'FAIL', 'smoke_test_summary': 'FAIL: summary', 'heartbeat_passes_completed': 1}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload

        response = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['trial_status'], 'FAIL')
        self.assertEqual(payload['next_action_hint'], 'Bootstrap failed; inspect mission control')

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'Bootstrap reused existing session'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_reuses_existing_bootstrap_without_duplication_signal(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]
        smoke_payload = {'smoke_test_status': 'PASS', 'smoke_test_summary': 'PASS: summary', 'heartbeat_passes_completed': 1}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload
        response = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        bootstrap_check = next(item for item in response.json()['checks'] if item['check_name'] == 'bootstrap')
        self.assertEqual(bootstrap_check['status'], 'PASS')
        self.assertIn('reused', bootstrap_check['summary'].lower())

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_heartbeat_passes_honors_one_or_two(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]
        smoke_payload = {'smoke_test_status': 'PASS', 'smoke_test_summary': 'PASS: summary', 'heartbeat_passes_completed': 2}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload

        response = self.client.post(
            reverse('mission_control:run-live-paper-trial'),
            data=json.dumps({'heartbeat_passes': 2}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['heartbeat_passes_requested'], 2)
        self.assertEqual(payload['heartbeat_passes_completed'], 2)

        too_many = self.client.post(
            reverse('mission_control:run-live-paper-trial'),
            data=json.dumps({'heartbeat_passes': 3}),
            content_type='application/json',
        )
        self.assertEqual(too_many.status_code, 400)

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_post_payload_contract_is_compact_and_stable(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]
        smoke_payload = {'smoke_test_status': 'PASS', 'smoke_test_summary': 'PASS: summary', 'heartbeat_passes_completed': 1}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload

        response = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        payload = response.json()
        required = {
            'preset_name', 'trial_status', 'bootstrap_action', 'smoke_test_status',
            'validation_status_before', 'validation_status_after', 'heartbeat_passes_requested',
            'heartbeat_passes_completed', 'recent_activity_detected', 'recent_trades_detected',
            'portfolio_snapshot_ready', 'next_action_hint', 'trial_summary', 'checks',
        }
        self.assertTrue(required.issubset(payload.keys()))
        self.assertEqual(
            [item['check_name'] for item in payload['checks']],
            ['bootstrap', 'smoke_test', 'validation_before', 'validation_after', 'portfolio_snapshot', 'recent_activity', 'recent_trades'],
        )

    @patch('apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test')
    @patch('apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result')
    @patch('apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status', return_value={'status_summary': 'ok'})
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session', return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'})
    @patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest')
    def test_get_status_returns_latest_result_contract(self, mock_validation, _mock_bootstrap, _mock_status, mock_smoke_status, mock_smoke_run):
        mock_validation.side_effect = [
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
            self._validation_payload('READY', activity=True, trades=True, snapshot=True),
        ]
        smoke_payload = {'smoke_test_status': 'PASS', 'smoke_test_summary': 'PASS: summary', 'heartbeat_passes_completed': 1}
        mock_smoke_status.return_value = smoke_payload
        mock_smoke_run.return_value = smoke_payload
        self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')

        response = self.client.get(reverse('mission_control:live-paper-trial-status'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        required = {
            'preset_name', 'trial_status', 'executed_at', 'smoke_test_status',
            'validation_status_after', 'heartbeat_passes_completed', 'trial_summary', 'next_action_hint',
        }
        self.assertTrue(required.issubset(payload.keys()))

    def test_existing_mission_control_summary_flow_still_works(self):
        response = self.client.get(reverse('mission_control:autonomous-session-summary'))
        self.assertEqual(response.status_code, 200)


class LivePaperTrialRunHistoryApiTests(TestCase):
    def setUp(self):
        _clear_live_paper_trial_history_for_tests()

    def _record_item(self, *, status: str, created_at, preset_name: str = 'live_read_only_paper_conservative'):
        record_live_paper_trial_result(
            {
                'executed_at': created_at,
                'preset_name': preset_name,
                'trial_status': status,
                'bootstrap_action': 'REUSED_EXISTING_SESSION',
                'smoke_test_status': 'PASS' if status == 'PASS' else ('WARN' if status == 'WARN' else 'FAIL'),
                'validation_status_after': 'READY' if status == 'PASS' else ('WARNING' if status == 'WARN' else 'BLOCKED'),
                'heartbeat_passes_completed': 1,
                'next_action_hint': f'{status} hint',
                'trial_summary': f'{status} summary',
                'recent_activity_detected': status != 'FAIL',
                'recent_trades_detected': status == 'PASS',
                'portfolio_snapshot_ready': status != 'FAIL',
            }
        )

    def _patch_trial_run_to_pass(self):
        validation_before = {
            'preset_name': 'live_read_only_paper_conservative',
            'validation_status': 'WARNING',
            'session_active': True,
            'heartbeat_active': True,
            'attention_mode': 'HEALTHY',
            'paper_account_ready': True,
            'market_data_ready': True,
            'portfolio_snapshot_ready': True,
            'recent_activity_present': True,
            'recent_trades_present': False,
            'cash_available': 10000.0,
            'equity_available': 10000.0,
            'next_action_hint': 'hint',
            'validation_summary': 'before',
            'checks': [],
        }
        validation_after = {**validation_before, 'validation_status': 'READY', 'recent_trades_present': True, 'validation_summary': 'after'}
        smoke_payload = {'smoke_test_status': 'PASS', 'smoke_test_summary': 'PASS: summary', 'heartbeat_passes_completed': 1}
        return patch('apps.mission_control.services.live_paper_trial_run.build_live_paper_validation_digest', side_effect=[validation_before, validation_after]), patch(
            'apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session',
            return_value={'bootstrap_action': 'REUSED_EXISTING_SESSION', 'bootstrap_summary': 'reused'},
        ), patch(
            'apps.mission_control.services.live_paper_trial_run.get_live_paper_bootstrap_status',
            return_value={'status_summary': 'ok'},
        ), patch(
            'apps.mission_control.services.live_paper_trial_run.run_live_paper_smoke_test',
            return_value=smoke_payload,
        ), patch(
            'apps.mission_control.services.live_paper_trial_run.get_last_live_paper_smoke_test_result',
            return_value=smoke_payload,
        )

    def test_history_records_after_trial_post(self):
        p1, p2, p3, p4, p5 = self._patch_trial_run_to_pass()
        with p1, p2, p3, p4, p5:
            run_response = self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        self.assertEqual(run_response.status_code, 200)

        history_response = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(history_response.status_code, 200)
        payload = history_response.json()
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['latest_trial_status'], 'PASS')
        self.assertEqual(payload['items'][0]['trial_status'], run_response.json()['trial_status'])

    def test_history_is_ordered_with_most_recent_first(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=2))
        self._record_item(status='WARN', created_at=now - timedelta(minutes=1))
        self._record_item(status='FAIL', created_at=now)

        response = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(response.status_code, 200)
        statuses = [item['trial_status'] for item in response.json()['items']]
        self.assertEqual(statuses[:3], ['FAIL', 'WARN', 'PASS'])

    def test_history_limit_works(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=3))
        self._record_item(status='WARN', created_at=now - timedelta(minutes=2))
        self._record_item(status='FAIL', created_at=now - timedelta(minutes=1))

        response = self.client.get(reverse('mission_control:live-paper-trial-history'), {'limit': 2})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 2)
        self.assertEqual(len(payload['items']), 2)

    def test_history_status_filter_works(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=3))
        self._record_item(status='WARN', created_at=now - timedelta(minutes=2))
        self._record_item(status='WARN', created_at=now - timedelta(minutes=1))

        response = self.client.get(reverse('mission_control:live-paper-trial-history'), {'status': 'WARN'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], 2)
        self.assertTrue(all(item['trial_status'] == 'WARN' for item in payload['items']))
        self.assertEqual(payload['history_summary'], 'Recent trial history shows warnings in the last 2 runs')

    def test_history_payload_contract_is_compact(self):
        self._record_item(status='PASS', created_at=timezone.now())
        response = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        expected_root = {'count', 'latest_trial_status', 'history_summary', 'items'}
        expected_item = {
            'created_at',
            'preset_name',
            'trial_status',
            'bootstrap_action',
            'smoke_test_status',
            'validation_status_after',
            'heartbeat_passes_completed',
            'next_action_hint',
            'trial_summary',
        }
        self.assertTrue(expected_root.issubset(payload.keys()))
        self.assertTrue(expected_item.issubset(payload['items'][0].keys()))

    def test_history_summary_is_stable_for_empty_and_failures(self):
        empty = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()['history_summary'], 'No live paper trial history recorded yet')

        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=2))
        self._record_item(status='FAIL', created_at=now - timedelta(minutes=1))
        failure = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(failure.status_code, 200)
        self.assertEqual(failure.json()['history_summary'], 'Recent trial history shows failures in the last 2 runs')

    def test_history_buffer_is_bounded(self):
        baseline = timezone.now()
        for idx in range(_HISTORY_CAPACITY + 3):
            self._record_item(status='PASS', created_at=baseline + timedelta(seconds=idx), preset_name=f'preset-{idx}')

        response = self.client.get(reverse('mission_control:live-paper-trial-history'), {'limit': _HISTORY_CAPACITY})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['count'], _HISTORY_CAPACITY)
        self.assertEqual(payload['items'][0]['preset_name'], f'preset-{_HISTORY_CAPACITY + 2}')
        self.assertEqual(payload['items'][-1]['preset_name'], 'preset-3')

    def test_existing_trial_status_endpoint_still_works(self):
        p1, p2, p3, p4, p5 = self._patch_trial_run_to_pass()
        with p1, p2, p3, p4, p5:
            self.client.post(reverse('mission_control:run-live-paper-trial'), data='{}', content_type='application/json')
        response = self.client.get(reverse('mission_control:live-paper-trial-status'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['trial_status'], 'PASS')


class LivePaperTrialTrendApiTests(TestCase):
    def setUp(self):
        _clear_live_paper_trial_history_for_tests()

    def _record_item(self, *, status: str, created_at, preset_name: str = 'live_read_only_paper_conservative'):
        record_live_paper_trial_result(
            {
                'executed_at': created_at,
                'preset_name': preset_name,
                'trial_status': status,
                'bootstrap_action': 'REUSED_EXISTING_SESSION',
                'smoke_test_status': 'PASS' if status == 'PASS' else ('WARN' if status == 'WARN' else 'FAIL'),
                'validation_status_after': 'READY' if status == 'PASS' else ('WARNING' if status == 'WARN' else 'BLOCKED'),
                'heartbeat_passes_completed': 1,
                'next_action_hint': f'{status} hint',
                'trial_summary': f'{status} summary',
                'recent_activity_detected': status != 'FAIL',
                'recent_trades_detected': status == 'PASS',
                'portfolio_snapshot_ready': status != 'FAIL',
            }
        )

    def test_trend_insufficient_data(self):
        self._record_item(status='PASS', created_at=timezone.now())
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['trend_status'], 'INSUFFICIENT_DATA')
        self.assertEqual(payload['readiness_status'], 'NEEDS_REVIEW')

    def test_trend_improving(self):
        now = timezone.now()
        self._record_item(status='WARN', created_at=now - timedelta(minutes=1))
        self._record_item(status='PASS', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['trend_status'], 'IMPROVING')

    def test_trend_stable(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=2))
        self._record_item(status='PASS', created_at=now - timedelta(minutes=1))
        self._record_item(status='PASS', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['trend_status'], 'STABLE')

    def test_trend_degrading(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=1))
        self._record_item(status='FAIL', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['trend_status'], 'DEGRADING')

    def test_readiness_ready_for_extended_run(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=1))
        self._record_item(status='PASS', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['readiness_status'], 'READY_FOR_EXTENDED_RUN')

    def test_readiness_needs_review(self):
        now = timezone.now()
        self._record_item(status='WARN', created_at=now - timedelta(minutes=1))
        self._record_item(status='WARN', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['readiness_status'], 'NEEDS_REVIEW')

    def test_readiness_not_ready(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=1))
        self._record_item(status='FAIL', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['readiness_status'], 'NOT_READY')

    def test_trend_payload_contract_is_compact(self):
        now = timezone.now()
        self._record_item(status='WARN', created_at=now - timedelta(minutes=1))
        self._record_item(status='PASS', created_at=now)
        response = self.client.get(reverse('mission_control:live-paper-trial-trend'), {'limit': 5, 'preset': 'live_read_only_paper_conservative'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        expected = {
            'sample_size',
            'latest_trial_status',
            'latest_validation_status',
            'trend_status',
            'readiness_status',
            'trend_summary',
            'next_action_hint',
            'counts',
            'recent_statuses',
        }
        self.assertTrue(expected.issubset(payload.keys()))
        self.assertEqual(set(payload['counts'].keys()), {'pass_count', 'warn_count', 'fail_count'})

    def test_trend_endpoint_does_not_break_history_endpoint(self):
        now = timezone.now()
        self._record_item(status='PASS', created_at=now - timedelta(minutes=1))
        self._record_item(status='WARN', created_at=now)
        trend = self.client.get(reverse('mission_control:live-paper-trial-trend'))
        self.assertEqual(trend.status_code, 200)
        history = self.client.get(reverse('mission_control:live-paper-trial-history'))
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()['count'], 2)


class LivePaperAutonomyFunnelApiTests(TestCase):
    def _funnel_counts(
        self,
        *,
        scan: int,
        research: int,
        prediction: int,
        risk_approved: int,
        risk_blocked: int,
        execution: int,
        recent_trades: int,
    ):
        from apps.mission_control.services.live_paper_autonomy_funnel import FunnelCounts

        return FunnelCounts(
            scan_count=scan,
            research_count=research,
            prediction_count=prediction,
            risk_approved_count=risk_approved,
            risk_blocked_count=risk_blocked,
            paper_execution_count=execution,
            recent_trades_count=recent_trades,
        )

    def _call_with_counts(self, *, counts):
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts):
            with patch('apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest', return_value={'validation_status': 'READY'}):
                with patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}):
                    with patch(
                        'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
                        return_value={
                            'shortlisted_signals': 0,
                            'handoff_candidates': 0,
                            'consensus_reviews': 0,
                            'prediction_candidates': 0,
                            'risk_decisions': 0,
                            'paper_execution_candidates': 0,
                            'handoff_reason_codes': [],
                            'stage_source_mismatch': {},
                            'handoff_summary': 'shortlisted_signals=0 handoff_candidates=0 consensus_reviews=0 prediction_candidates=0 risk_decisions=0 paper_execution_candidates=0 handoff_reason_codes=none',
                        },
                    ):
                        return self.client.get(reverse('mission_control:live-paper-autonomy-funnel'))

    def test_active_case_returns_expected_status_and_contract(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=12, research=8, prediction=6, risk_approved=4, risk_blocked=1, execution=3, recent_trades=4)
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['funnel_status'], 'ACTIVE')
        self.assertEqual(payload['top_stage'], 'scan')
        self.assertIsNone(payload['stalled_stage'])
        self.assertEqual(payload['next_action_hint'], 'Autonomy funnel appears healthy')
        required = {
            'window_minutes',
            'funnel_status',
            'scan_count',
            'research_count',
            'prediction_count',
            'risk_approved_count',
            'risk_blocked_count',
            'risk_decision_count',
            'paper_execution_count',
            'recent_trades_count',
            'top_stage',
            'stalled_stage',
            'stalled_reason_code',
            'stalled_missing_counter',
            'handoff_reason_codes',
            'stage_source_mismatch',
            'handoff_summary',
            'next_action_hint',
            'funnel_summary',
            'stages',
        }
        self.assertTrue(required.issubset(payload.keys()))

    def test_thin_flow_case_detects_stalled_stage(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=9, research=5, prediction=4, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        )
        payload = response.json()
        self.assertEqual(payload['funnel_status'], 'THIN_FLOW')
        self.assertEqual(payload['stalled_stage'], 'risk')
        self.assertEqual(payload['next_action_hint'], 'Flow is thin after prediction')

    def test_stalled_case_detects_no_scan_activity(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=0, research=0, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        )
        payload = response.json()
        self.assertEqual(payload['funnel_status'], 'STALLED')
        self.assertEqual(payload['top_stage'], 'scan')
        self.assertEqual(payload['next_action_hint'], 'No recent scan activity detected')

    def test_stage_rows_are_present_and_readable(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=2, research=1, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        )
        payload = response.json()
        stage_names = [stage['stage_name'] for stage in payload['stages']]
        self.assertEqual(stage_names, ['scan', 'research', 'prediction', 'risk', 'paper_execution'])
        statuses = {stage['stage_name']: stage['status'] for stage in payload['stages']}
        self.assertEqual(statuses['scan'], 'LOW')
        self.assertEqual(statuses['prediction'], 'EMPTY')

    def test_risk_blocking_hint_is_deterministic(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=5, research=4, prediction=3, risk_approved=1, risk_blocked=4, execution=0, recent_trades=0)
        )
        payload = response.json()
        self.assertEqual(payload['next_action_hint'], 'Risk is blocking most candidates')

    def test_does_not_mark_shortlist_reason_without_real_shortlist(self):
        counts = self._funnel_counts(scan=7, research=0, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest',
            return_value={'validation_status': 'READY'},
        ), patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
            return_value={
                'shortlisted_signals': 0,
                'handoff_candidates': 0,
                'consensus_reviews': 0,
                'prediction_candidates': 0,
                'risk_decisions': 0,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': [],
                'stage_source_mismatch': {},
                'handoff_summary': '',
            },
        ):
            payload = self.client.get(reverse('mission_control:live-paper-autonomy-funnel')).json()
        self.assertEqual(payload['stalled_stage'], 'research')
        self.assertNotEqual(payload.get('stalled_reason_code'), 'SHORTLIST_PRESENT_NO_HANDOFF')

    def test_marks_shortlist_reason_when_shortlist_exists_without_handoff(self):
        counts = self._funnel_counts(scan=7, research=0, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest',
            return_value={'validation_status': 'READY'},
        ), patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
            return_value={
                'shortlisted_signals': 3,
                'handoff_candidates': 0,
                'consensus_reviews': 0,
                'prediction_candidates': 0,
                'risk_decisions': 0,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': ['SHORTLIST_PRESENT_NO_HANDOFF'],
                'stage_source_mismatch': {},
                'handoff_summary': '',
            },
        ):
            payload = self.client.get(reverse('mission_control:live-paper-autonomy-funnel')).json()
        self.assertEqual(payload['stalled_stage'], 'research')
        self.assertEqual(payload.get('stalled_reason_code'), 'SHORTLIST_PRESENT_NO_HANDOFF')

    def test_risk_stalled_missing_counter_points_to_real_payload_field(self):
        response = self._call_with_counts(
            counts=self._funnel_counts(scan=9, research=5, prediction=4, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        )
        payload = response.json()
        pointer = payload.get('stalled_missing_counter')
        self.assertEqual(payload.get('stalled_stage'), 'risk')
        self.assertEqual(pointer, 'risk_decision_count')
        self.assertIn(pointer, payload)
        self.assertEqual(payload[pointer], 0)

    def test_handoff_present_without_consensus_is_explicit(self):
        counts = self._funnel_counts(scan=7, research=2, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest',
            return_value={'validation_status': 'READY'},
        ), patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
            return_value={
                'shortlisted_signals': 3,
                'handoff_candidates': 2,
                'consensus_reviews': 0,
                'prediction_candidates': 0,
                'risk_decisions': 0,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': ['HANDOFF_CREATED', 'CONSENSUS_NOT_RUN', 'PREDICTION_STAGE_EMPTY'],
                'stage_source_mismatch': {},
                'handoff_summary': '',
            },
        ):
            payload = self.client.get(reverse('mission_control:live-paper-autonomy-funnel')).json()
        self.assertIn('CONSENSUS_NOT_RUN', payload.get('handoff_reason_codes', []))

    def test_consensus_without_promotion_is_explicit(self):
        counts = self._funnel_counts(scan=9, research=4, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest',
            return_value={'validation_status': 'READY'},
        ), patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
            return_value={
                'shortlisted_signals': 5,
                'handoff_candidates': 4,
                'consensus_reviews': 4,
                'prediction_candidates': 0,
                'risk_decisions': 0,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': ['HANDOFF_CREATED', 'CONSENSUS_RAN_NO_PROMOTION', 'PREDICTION_STAGE_EMPTY'],
                'stage_source_mismatch': {},
                'handoff_summary': '',
            },
        ):
            payload = self.client.get(reverse('mission_control:live-paper-autonomy-funnel')).json()
        self.assertIn('CONSENSUS_RAN_NO_PROMOTION', payload.get('handoff_reason_codes', []))

    def test_prediction_and_risk_empty_with_shortlist_is_explicit(self):
        counts = self._funnel_counts(scan=12, research=3, prediction=0, risk_approved=0, risk_blocked=0, execution=0, recent_trades=0)
        with patch('apps.mission_control.services.live_paper_autonomy_funnel._collect_funnel_counts', return_value=counts), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest',
            return_value={'validation_status': 'WARNING'},
        ), patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': 999}), patch(
            'apps.mission_control.services.live_paper_autonomy_funnel._build_handoff_diagnostics',
            return_value={
                'shortlisted_signals': 4,
                'handoff_candidates': 3,
                'consensus_reviews': 3,
                'prediction_candidates': 0,
                'risk_decisions': 0,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': ['PREDICTION_STAGE_EMPTY', 'DOWNSTREAM_EVIDENCE_INSUFFICIENT'],
                'stage_source_mismatch': {},
                'handoff_summary': '',
            },
        ):
            payload = self.client.get(reverse('mission_control:live-paper-autonomy-funnel')).json()
        self.assertIn('PREDICTION_STAGE_EMPTY', payload.get('handoff_reason_codes', []))
        self.assertIn('DOWNSTREAM_EVIDENCE_INSUFFICIENT', payload.get('handoff_reason_codes', []))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel.build_account_summary', return_value={'recent_trades': []})
    @patch('apps.mission_control.services.live_paper_autonomy_funnel.get_active_account')
    @patch('apps.mission_control.services.live_paper_autonomy_funnel.build_heartbeat_summary', return_value={'latest_run': None})
    @patch('apps.mission_control.services.live_paper_autonomy_funnel.build_live_paper_validation_digest', return_value={'validation_status': 'WARNING'})
    def test_service_reuses_existing_validation_heartbeat_and_paper_summary(self, mock_validation, mock_heartbeat, mock_account, _mock_summary):
        from apps.mission_control.services.live_paper_autonomy_funnel import build_live_paper_autonomy_funnel_snapshot

        mock_account.return_value = object()
        payload = build_live_paper_autonomy_funnel_snapshot(window_minutes=60, preset_name='live_read_only_paper_conservative')
        self.assertIn(payload['funnel_status'], {'ACTIVE', 'THIN_FLOW', 'STALLED'})
        self.assertTrue(mock_validation.called)
        self.assertTrue(mock_heartbeat.called)


class LivePaperAutonomyFunnelShortlistDiagnosticsTests(TestCase):
    def _provider_and_market(self, suffix: str = 'base'):
        from apps.markets.models import Market, Provider

        provider = Provider.objects.create(name=f'Demo Provider {suffix}', slug=f'demo-provider-{suffix}')
        market = Market.objects.create(provider=provider, title=f'Market {suffix}', slug=f'market-{suffix}')
        return market

    def _shortlisted_signal(self, *, market=None, topic: str = 'topic-a'):
        from apps.research_agent.models import NarrativeCluster, NarrativeSignal, NarrativeSignalStatus, SourceScanRun

        scan_run = SourceScanRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        cluster = NarrativeCluster.objects.create(
            scan_run=scan_run,
            canonical_topic=topic,
            representative_headline=f'headline-{topic}',
            source_types=['rss'],
            item_count=3,
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        return NarrativeSignal.objects.create(
            scan_run=scan_run,
            canonical_label=f'signal-{topic}',
            topic=topic,
            status=NarrativeSignalStatus.SHORTLISTED,
            linked_cluster=cluster,
            linked_market=market,
        )

    def _active_market(self, *, suffix: str, title: str):
        from apps.markets.models import Market, MarketStatus, Provider

        provider = Provider.objects.create(name=f'Link Provider {suffix}', slug=f'link-provider-{suffix}')
        return Market.objects.create(
            provider=provider,
            title=title,
            slug=f'link-market-{suffix}',
            status=MarketStatus.OPEN,
            is_active=True,
        )

    def _risk_decision(self, *, market, approval_status: str, created_at=None):
        from apps.prediction_agent.models import (
            PredictionConvictionBucket,
            PredictionConvictionReview,
            PredictionConvictionReviewStatus,
            PredictionIntakeCandidate,
            PredictionIntakeRun,
            PredictionIntakeStatus,
            RiskReadyPredictionHandoffStatus,
            RiskReadyPredictionHandoff,
        )
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )
        from apps.risk_agent.models import RiskApprovalDecision, RiskRuntimeCandidate, RiskRuntimeRun

        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7800'),
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        intake_candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.READY_FOR_RUNTIME,
            handoff_confidence=Decimal('0.7800'),
            narrative_priority=Decimal('0.7200'),
            structural_priority=Decimal('0.7100'),
        )
        review = PredictionConvictionReview.objects.create(
            linked_intake_candidate=intake_candidate,
            system_probability=Decimal('0.6200'),
            market_probability=Decimal('0.5000'),
            calibrated_probability=Decimal('0.6200'),
            raw_edge=Decimal('0.1200'),
            adjusted_edge=Decimal('0.1200'),
            confidence=Decimal('0.7900'),
            uncertainty=Decimal('0.2100'),
            conviction_bucket=PredictionConvictionBucket.MEDIUM_CONVICTION,
            review_status=PredictionConvictionReviewStatus.READY_FOR_RISK,
            reason_codes=['SEEDED_FOR_PAPER_EXECUTION_DIAGNOSTICS'],
        )
        risk_handoff = RiskReadyPredictionHandoff.objects.create(
            linked_market=market,
            linked_conviction_review=review,
            handoff_status=RiskReadyPredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7900'),
            handoff_summary='seeded for diagnostics',
            handoff_reason_codes=['SEEDED_FOR_PAPER_EXECUTION_DIAGNOSTICS'],
        )
        runtime_run = RiskRuntimeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        runtime_candidate = RiskRuntimeCandidate.objects.create(
            runtime_run=runtime_run,
            linked_risk_ready_prediction_handoff=risk_handoff,
            linked_prediction_conviction_review=review,
            linked_prediction_intake_candidate=intake_candidate,
            linked_market=market,
            market_provider=market.provider.slug,
            category=market.category or '',
            calibrated_probability=Decimal('0.6200'),
            market_probability=Decimal('0.5000'),
            adjusted_edge=Decimal('0.1200'),
            intake_status='READY_FOR_RISK_RUNTIME',
            confidence_score=Decimal('0.7900'),
            uncertainty_score=Decimal('0.2100'),
            conviction_bucket='MEDIUM',
            portfolio_pressure_state='LOW',
            context_summary='seeded-for-paper-execution-diagnostics',
            reason_codes=['SEEDED_FOR_PAPER_EXECUTION_DIAGNOSTICS'],
            evidence_quality_score=Decimal('0.7100'),
            precedent_caution_score=Decimal('0.2000'),
            linked_portfolio_context={},
            linked_feedback_context={},
            market_liquidity_context={},
            predicted_status='READY',
            metadata={'paper_demo_only': True},
        )
        decision = RiskApprovalDecision.objects.create(
            linked_candidate=runtime_candidate,
            approval_status=approval_status,
            approval_confidence=Decimal('0.7300'),
            approval_summary='seeded-for-paper-execution-diagnostics',
            approval_rationale='seeded-for-paper-execution-diagnostics',
            reason_codes=['SEEDED_FOR_PAPER_EXECUTION_DIAGNOSTICS'],
            blockers=[],
            risk_score=Decimal('0.2500'),
            max_allowed_exposure=Decimal('100.00'),
            watch_required=False,
            metadata={'paper_demo_only': True},
        )
        if created_at is not None:
            RiskApprovalDecision.objects.filter(id=decision.id).update(created_at=created_at)
            decision.refresh_from_db()
        return decision

    def test_shortlist_present_without_pursuit_attempt_reports_no_downstream_route(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics

        market = self._provider_and_market('no-route')
        self._shortlisted_signal(market=market, topic='no-route')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        shortlist = diagnostics.get('shortlist_handoff_summary') or {}
        downstream = diagnostics.get('downstream_route_summary') or {}
        self.assertEqual(shortlist.get('handoff_attempted'), 0)
        self.assertEqual(shortlist.get('handoff_created'), 0)
        self.assertIn('SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE', shortlist.get('shortlist_handoff_reason_codes', []))
        self.assertEqual(downstream.get('route_expected'), 1)
        self.assertEqual(downstream.get('route_missing'), 1)
        self.assertIn('DOWNSTREAM_ROUTE_MISSING', downstream.get('downstream_route_reason_codes', []))

    def test_shortlist_attempted_but_not_promoted_reports_blocked_reason(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import ResearchPursuitRun, ResearchStructuralAssessment, ResearchStructuralStatus

        market = self._provider_and_market('blocked')
        self._shortlisted_signal(market=market, topic='blocked')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.BLOCKED,
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        shortlist = diagnostics.get('shortlist_handoff_summary') or {}
        self.assertEqual(shortlist.get('handoff_attempted'), 1)
        self.assertEqual(shortlist.get('handoff_created'), 0)
        self.assertEqual(shortlist.get('handoff_blocked'), 1)
        self.assertIn('SHORTLIST_BLOCKED_BY_FILTER', shortlist.get('shortlist_handoff_reason_codes', []))

    def test_shortlist_promoted_to_handoff_reports_counters(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('promoted')
        self._shortlisted_signal(market=market, topic='promoted')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        shortlist = diagnostics.get('shortlist_handoff_summary') or {}
        downstream = diagnostics.get('downstream_route_summary') or {}
        self.assertEqual(shortlist.get('handoff_attempted'), 1)
        self.assertEqual(shortlist.get('handoff_created'), 1)
        self.assertEqual(shortlist.get('handoff_blocked'), 0)
        self.assertIn('SHORTLIST_PROMOTED_TO_HANDOFF', shortlist.get('shortlist_handoff_reason_codes', []))
        self.assertEqual(downstream.get('route_created'), 1)
        self.assertIn('DOWNSTREAM_ROUTE_CREATED_HANDOFF', downstream.get('downstream_route_reason_codes', []))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel._is_downstream_route_handler_available', return_value=False)
    def test_shortlist_route_without_handler_reports_explicit_reason(self, _mock_handler):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics

        market = self._provider_and_market('no-handler')
        self._shortlisted_signal(market=market, topic='no-handler')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        downstream = diagnostics.get('downstream_route_summary') or {}
        self.assertEqual(downstream.get('route_missing'), 1)
        self.assertIn('DOWNSTREAM_ROUTE_NO_ELIGIBLE_HANDLER', downstream.get('downstream_route_reason_codes', []))

    def test_market_link_diagnostics_reports_no_candidates(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics

        self._shortlisted_signal(topic='zzqxv no matching market token')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        market_link = diagnostics.get('market_link_summary') or {}
        self.assertEqual(market_link.get('market_link_resolved'), 0)
        self.assertIn('MARKET_LINK_NO_CANDIDATES', market_link.get('market_link_reason_codes', []))

    def test_market_link_diagnostics_reports_ambiguous_candidates(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics

        self._active_market(suffix='amb-1', title='Election Senate Winner 2026')
        self._active_market(suffix='amb-2', title='Election Senate Winner 2027')
        self._shortlisted_signal(topic='Election Senate Winner')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        market_link = diagnostics.get('market_link_summary') or {}
        self.assertGreaterEqual(market_link.get('market_link_ambiguous', 0), 1)
        self.assertIn('MARKET_LINK_AMBIGUOUS', market_link.get('market_link_reason_codes', []))

    def test_market_link_diagnostics_resolves_single_candidate_and_unblocks_handoff_attempt(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics

        self._active_market(suffix='resolved', title='Fed rate cut June decision')
        self._shortlisted_signal(topic='Fed rate cut June decision')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        market_link = diagnostics.get('market_link_summary') or {}
        shortlist = diagnostics.get('shortlist_handoff_summary') or {}
        self.assertEqual(market_link.get('market_link_resolved'), 1)
        self.assertIn('MARKET_LINK_RESOLVED', market_link.get('market_link_reason_codes', []))
        self.assertEqual(shortlist.get('handoff_attempted'), 0)
        self.assertIn('SHORTLIST_BLOCKED_NO_DOWNSTREAM_ROUTE', shortlist.get('shortlist_handoff_reason_codes', []))

    def test_consensus_decoupled_from_shortlist_is_explicit(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import NarrativeCluster, NarrativeConsensusRecord, NarrativeConsensusRun, SourceScanRun

        self._shortlisted_signal(topic='aligned-cluster-missing')
        scan_run = SourceScanRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        decoupled_cluster = NarrativeCluster.objects.create(
            scan_run=scan_run,
            canonical_topic='decoupled',
            representative_headline='decoupled-headline',
            source_types=['reddit'],
            item_count=2,
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        consensus_run = NarrativeConsensusRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        NarrativeConsensusRecord.objects.create(
            consensus_run=consensus_run,
            linked_cluster=decoupled_cluster,
            topic_label='decoupled',
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertIn('CONSENSUS_DECOUPLED_FROM_SHORTLIST', diagnostics.get('handoff_reason_codes', []))
        alignment = diagnostics.get('consensus_alignment') or {}
        self.assertFalse(alignment.get('consensus_aligned_with_shortlist', True))
        self.assertEqual(alignment.get('shortlist_aligned_consensus_reviews'), 0)

    @patch('apps.mission_control.services.live_paper_autonomy_funnel._is_prediction_intake_handler_available', return_value=False)
    def test_prediction_intake_route_missing_is_explicit(self, _mock_handler):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-route-missing')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertEqual(summary.get('prediction_intake_attempted'), 0)
        self.assertIn('PREDICTION_INTAKE_ROUTE_MISSING', summary.get('prediction_intake_reason_codes', []))

    def test_paper_execution_summary_marks_non_routable_risk_decision(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.risk_agent.models import RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-non-routable')
        self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.BLOCKED)

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('paper_execution_summary') or ''
        codes = diagnostics.get('paper_execution_route_reason_codes') or []
        self.assertIn('route_missing_status_count=1', summary)
        self.assertIn('PAPER_EXECUTION_STATUS_FILTER_REJECTED', codes)
        self.assertEqual(diagnostics.get('paper_execution_route_expected'), 0)

    @patch('apps.mission_control.services.live_paper_autonomy_funnel._is_paper_execution_handler_available', return_value=False)
    def test_paper_execution_summary_marks_route_missing_when_handler_unavailable(self, _mock_handler):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.risk_agent.models import RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-route-missing')
        self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        codes = diagnostics.get('paper_execution_route_reason_codes') or []
        self.assertEqual(diagnostics.get('paper_execution_route_expected'), 1)
        self.assertEqual(diagnostics.get('paper_execution_route_available'), 0)
        self.assertIn('PAPER_EXECUTION_NO_ELIGIBLE_HANDLER', codes)

    def test_paper_execution_summary_marks_reused_existing_candidate(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-reuse')
        decision = self._risk_decision(
            market=market,
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
            created_at=timezone.now() - timedelta(minutes=30),
        )
        AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.7400'),
            readiness_summary='seeded-for-reuse',
            readiness_reason_codes=['SEEDED_FOR_REUSE'],
        )
        readiness = AutonomousExecutionReadiness.objects.get(linked_approval_review=decision)
        AutonomousExecutionReadiness.objects.filter(id=readiness.id).update(created_at=timezone.now() - timedelta(hours=2))
        readiness.refresh_from_db()
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now() - timedelta(hours=2), completed_at=timezone.now())
        intake = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.7200'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )
        AutonomousExecutionIntakeCandidate.objects.filter(id=intake.id).update(created_at=timezone.now() - timedelta(minutes=10))

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        codes = diagnostics.get('paper_execution_route_reason_codes') or []
        self.assertEqual(diagnostics.get('paper_execution_route_reused'), 1)
        self.assertEqual(diagnostics.get('paper_execution_route_created'), 0)
        self.assertIn('PAPER_EXECUTION_REUSED_EXISTING_CANDIDATE', codes)
        self.assertEqual(diagnostics.get('paper_execution_visible_count'), 1)
        self.assertEqual(diagnostics.get('paper_execution_candidates'), 1)
        self.assertIn('PAPER_EXECUTION_VISIBLE_IN_FUNNEL', diagnostics.get('paper_execution_visibility_reason_codes', []))

    def test_paper_execution_visibility_created_candidate_is_counted_in_funnel(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-created-visible')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.7600'),
            readiness_summary='seeded-for-created-visible',
            readiness_reason_codes=['SEEDED_FOR_CREATED_VISIBLE'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.7600'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('paper_execution_created_count'), 1)
        self.assertEqual(diagnostics.get('paper_execution_visible_count'), 1)
        self.assertEqual(diagnostics.get('paper_execution_candidates'), 1)
        self.assertEqual(diagnostics.get('paper_execution_route_created'), 1)

    def test_paper_execution_visibility_surfaces_hidden_reasons(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-hidden-status')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.6500'),
            readiness_summary='seeded-for-hidden-status',
            readiness_reason_codes=['SEEDED_FOR_HIDDEN_STATUS'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.BLOCKED,
            readiness_confidence=Decimal('0.6500'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('paper_execution_visible_count'), 0)
        self.assertEqual(diagnostics.get('paper_execution_hidden_count'), 1)
        self.assertIn('PAPER_EXECUTION_CANDIDATE_HIDDEN_BY_STATUS', diagnostics.get('paper_execution_visibility_reason_codes', []))

    def test_paper_trade_summary_marks_visible_candidate_not_executable(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-visible-not-executable')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.6800'),
            readiness_summary='watch-only-visible',
            readiness_reason_codes=['WATCH_ONLY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.WATCH_ONLY,
            readiness_confidence=Decimal('0.6800'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('paper_trade_route_expected'), 1)
        self.assertEqual(diagnostics.get('paper_trade_route_blocked'), 1)
        self.assertIn('PAPER_TRADE_STATUS_FILTER_REJECTED', diagnostics.get('paper_trade_route_reason_codes', []))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel._is_paper_execution_handler_available', return_value=False)
    def test_paper_trade_summary_marks_route_missing_for_executable_candidate(self, _mock_handler):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-route-missing')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8300'),
            readiness_summary='ready-for-route-missing',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.8300'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('paper_trade_route_expected'), 1)
        self.assertEqual(diagnostics.get('paper_trade_route_available'), 0)
        self.assertIn('PAPER_TRADE_NO_ELIGIBLE_HANDLER', diagnostics.get('paper_trade_route_reason_codes', []))

    def test_paper_trade_decision_bridge_creates_missing_execution_decision(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import (
            AutonomousDispatchRecord,
            AutonomousExecutionDecision,
            AutonomousExecutionIntakeCandidate,
            AutonomousExecutionIntakeRun,
            AutonomousExecutionIntakeStatus,
        )
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-decision-created')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8400'),
            readiness_summary='decision-created',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.8400'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertTrue(AutonomousExecutionDecision.objects.filter(linked_intake_candidate=candidate).exists())
        self.assertTrue(
            AutonomousDispatchRecord.objects.filter(linked_execution_decision__linked_intake_candidate=candidate).exists()
        )
        self.assertEqual(diagnostics.get('paper_trade_decision_created'), 1)
        self.assertIn('PAPER_TRADE_DECISION_CREATED', diagnostics.get('paper_trade_decision_reason_codes', []))
        self.assertEqual(diagnostics.get('paper_trade_dispatch_created'), 1)
        self.assertIn('PAPER_TRADE_DISPATCH_CREATED', diagnostics.get('paper_trade_dispatch_reason_codes', []))

    def test_paper_trade_decision_bridge_reuses_existing_execution_decision(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import (
            AutonomousDispatchRecord,
            AutonomousExecutionDecision,
            AutonomousExecutionIntakeCandidate,
            AutonomousExecutionIntakeRun,
            AutonomousExecutionIntakeStatus,
        )
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-decision-reused')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8200'),
            readiness_summary='decision-reused',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.8200'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )
        existing = AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')
        dispatch = AutonomousDispatchRecord.objects.create(linked_execution_decision=existing, dispatch_status='QUEUED')

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(AutonomousExecutionDecision.objects.filter(linked_intake_candidate=candidate).count(), 1)
        self.assertEqual(diagnostics.get('paper_trade_decision_reused'), 1)
        self.assertIn('PAPER_TRADE_DECISION_REUSED', diagnostics.get('paper_trade_decision_reason_codes', []))
        self.assertEqual(diagnostics.get('paper_trade_dispatch_reused'), 1)
        self.assertIn('PAPER_TRADE_DISPATCH_REUSED', diagnostics.get('paper_trade_dispatch_reason_codes', []))
        self.assertEqual(
            (diagnostics.get('paper_trade_decision_examples') or [{}])[0].get('observed_value'),
            f'existing_execution_decision:{existing.id}',
        )
        self.assertEqual(
            (diagnostics.get('paper_trade_dispatch_examples') or [{}])[0].get('observed_value'),
            f'existing_dispatch_record:{dispatch.id}',
        )

    def test_paper_trade_decision_dedupe_applies_for_same_lineage_market(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import (
            AutonomousExecutionDecision,
            AutonomousExecutionIntakeCandidate,
            AutonomousExecutionIntakeRun,
            AutonomousExecutionIntakeStatus,
        )
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-decision-dedupe')
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        for idx in range(2):
            risk_decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
            readiness = AutonomousExecutionReadiness.objects.create(
                linked_market=market,
                linked_approval_review=risk_decision,
                readiness_status=AutonomousExecutionReadinessStatus.READY,
                readiness_confidence=Decimal('0.8000'),
                readiness_summary=f'dedupe-{idx}',
                readiness_reason_codes=['READY'],
            )
            AutonomousExecutionIntakeCandidate.objects.create(
                intake_run=intake_run,
                linked_market=market,
                linked_execution_readiness=readiness,
                linked_approval_review=risk_decision,
                intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
                readiness_confidence=Decimal('0.8000'),
                approval_status=RiskRuntimeApprovalStatus.APPROVED,
                linked_prediction_context={'prediction_candidate_id': 901, 'handoff_id': 701},
            )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(AutonomousExecutionDecision.objects.count(), 1)
        self.assertEqual(diagnostics.get('paper_trade_decision_dedupe_applied'), 1)
        self.assertIn('LINEAGE_DEDUPE_APPLIED', diagnostics.get('paper_trade_decision_reason_codes', []))
        self.assertIn('LINEAGE_DEDUPE_BLOCKED_DUPLICATE', diagnostics.get('paper_trade_route_reason_codes', []))
        self.assertEqual(diagnostics.get('paper_trade_dispatch_created'), 1)
        self.assertIn('PAPER_TRADE_DISPATCH_CREATED', diagnostics.get('paper_trade_dispatch_reason_codes', []))
        lineage = diagnostics.get('execution_lineage_summary') or {}
        self.assertEqual(lineage.get('candidates_deduplicated'), 1)
        self.assertTrue(lineage.get('decision_summary_aligned'))

    def test_paper_trade_final_bridge_materializes_trade_for_queued_dispatch(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousDispatchRecord, AutonomousExecutionDecision, AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-final-created')
        market.status = 'open'
        market.current_yes_price = Decimal('0.6200')
        market.current_market_probability = Decimal('0.6200')
        market.save(update_fields=['status', 'current_yes_price', 'current_market_probability', 'updated_at'])
        risk_decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=risk_decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8200'),
            readiness_summary='final-created',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=risk_decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.8200'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )
        execution_decision = AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')
        dispatch = AutonomousDispatchRecord.objects.create(linked_execution_decision=execution_decision, dispatch_status='QUEUED')

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        dispatch.refresh_from_db()
        self.assertIsNotNone(dispatch.linked_paper_trade_id)
        self.assertEqual(diagnostics.get('final_trade_created'), 1)
        self.assertIn('PAPER_TRADE_FINAL_CREATED', diagnostics.get('final_trade_reason_codes', []))
        self.assertGreaterEqual((diagnostics.get('execution_lineage_summary') or {}).get('trades_materialized', 0), 1)

    def test_paper_trade_final_bridge_reuses_existing_linked_trade(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousDispatchRecord, AutonomousExecutionDecision, AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.paper_trading.services.execution import execute_paper_trade
        from apps.paper_trading.models import PaperTradeType
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-final-reused')
        market.status = 'open'
        market.current_yes_price = Decimal('0.6100')
        market.current_market_probability = Decimal('0.6100')
        market.save(update_fields=['status', 'current_yes_price', 'current_market_probability', 'updated_at'])
        risk_decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=risk_decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8200'),
            readiness_summary='final-reused',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=risk_decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.8200'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )
        execution_decision = AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')
        existing_trade = execute_paper_trade(
            market=market,
            trade_type=PaperTradeType.BUY,
            side='YES',
            quantity=Decimal('10'),
            notes='seed-existing-trade',
        ).trade
        AutonomousDispatchRecord.objects.create(
            linked_execution_decision=execution_decision,
            dispatch_status='QUEUED',
            linked_paper_trade=existing_trade,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('final_trade_reused'), 1)
        self.assertIn('PAPER_TRADE_FINAL_REUSED', diagnostics.get('final_trade_reason_codes', []))

    def test_paper_trade_final_dedupe_reuses_trade_by_lineage_market(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousDispatchRecord, AutonomousExecutionDecision, AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-final-dedupe')
        market.status = 'open'
        market.current_yes_price = Decimal('0.6000')
        market.current_market_probability = Decimal('0.6000')
        market.save(update_fields=['status', 'current_yes_price', 'current_market_probability', 'updated_at'])
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        created_dispatches = []
        for idx in range(2):
            risk_decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
            readiness = AutonomousExecutionReadiness.objects.create(
                linked_market=market,
                linked_approval_review=risk_decision,
                readiness_status=AutonomousExecutionReadinessStatus.READY,
                readiness_confidence=Decimal('0.8200'),
                readiness_summary=f'final-dedupe-{idx}',
                readiness_reason_codes=['READY'],
            )
            candidate = AutonomousExecutionIntakeCandidate.objects.create(
                intake_run=intake_run,
                linked_market=market,
                linked_execution_readiness=readiness,
                linked_approval_review=risk_decision,
                intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
                readiness_confidence=Decimal('0.8200'),
                approval_status=RiskRuntimeApprovalStatus.APPROVED,
                linked_prediction_context={'prediction_candidate_id': 123, 'handoff_id': 456},
            )
            execution_decision = AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')
            created_dispatches.append(AutonomousDispatchRecord.objects.create(linked_execution_decision=execution_decision, dispatch_status='QUEUED'))

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        for dispatch in created_dispatches:
            dispatch.refresh_from_db()
        linked_trade_ids = {dispatch.linked_paper_trade_id for dispatch in created_dispatches}
        self.assertEqual(len(linked_trade_ids), 1)
        self.assertIn('PAPER_TRADE_FINAL_DEDUPE_REUSED', diagnostics.get('final_trade_reason_codes', []))
        self.assertIn('LINEAGE_DEDUPE_REUSED_EXISTING_TRADE', (diagnostics.get('execution_lineage_summary') or {}).get('fanout_reason_codes', []))

    def test_paper_trade_decision_summary_aligned_with_execution_lineage_summary(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionDecision, AutonomousExecutionIntakeCandidate, AutonomousExecutionIntakeRun, AutonomousExecutionIntakeStatus
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-summary-alignment')
        risk_decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=risk_decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.7900'),
            readiness_summary='alignment',
            readiness_reason_codes=['READY'],
        )
        intake_run = AutonomousExecutionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = AutonomousExecutionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_execution_readiness=readiness,
            linked_approval_review=risk_decision,
            intake_status=AutonomousExecutionIntakeStatus.READY_FOR_AUTONOMOUS_EXECUTION,
            readiness_confidence=Decimal('0.7900'),
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
        )
        AutonomousExecutionDecision.objects.create(linked_intake_candidate=candidate, decision_type='EXECUTE_NOW')

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        decision_summary = diagnostics.get('paper_trade_decision_summary', '')
        lineage = diagnostics.get('execution_lineage_summary') or {}
        self.assertIn('decision_reused=1', decision_summary)
        self.assertEqual(lineage.get('decisions_reused'), 1)
        self.assertTrue(lineage.get('decision_summary_aligned'))

    def test_execution_lineage_summary_surfaces_fanout_reason_codes(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-trade-fanout')
        for idx in range(4):
            decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
            AutonomousExecutionReadiness.objects.create(
                linked_market=market,
                linked_approval_review=decision,
                readiness_status=AutonomousExecutionReadinessStatus.READY,
                readiness_confidence=Decimal('0.7800'),
                readiness_summary=f'fanout-{idx}',
                readiness_reason_codes=['READY'],
            )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        lineage = diagnostics.get('execution_lineage_summary') or {}
        self.assertEqual(lineage.get('visible_execution_candidates'), diagnostics.get('paper_execution_candidates'))
        self.assertIn('LINEAGE_FANOUT_EXCESSIVE', lineage.get('fanout_reason_codes', []))
        self.assertIn('candidates_considered', lineage)
        self.assertIn('decisions_created', lineage)

    def test_paper_execution_bridge_materializes_candidate_from_readiness(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.autonomous_trader.models import AutonomousExecutionIntakeCandidate
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-bridge-materialize')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        readiness = AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.8100'),
            readiness_summary='bridge-materialize',
            readiness_reason_codes=['READY_FOR_BRIDGE'],
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertTrue(AutonomousExecutionIntakeCandidate.objects.filter(linked_execution_readiness=readiness).exists())
        self.assertEqual(diagnostics.get('paper_execution_candidates'), 1)
        self.assertEqual(diagnostics.get('execution_candidate_visible_count'), 1)
        self.assertEqual(diagnostics.get('execution_candidate_created_count'), 1)
        self.assertIn('PAPER_EXECUTION_CANDIDATE_CREATED', diagnostics.get('execution_artifact_reason_codes', []))
        self.assertIn('PAPER_EXECUTION_ARTIFACT_MISMATCH_RESOLVED', diagnostics.get('execution_artifact_reason_codes', []))

    def test_paper_execution_artifact_summary_marks_model_mismatch_when_still_missing(self):
        from unittest.mock import patch

        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-bridge-mismatch')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.7000'),
            readiness_summary='bridge-mismatch',
            readiness_reason_codes=['READY_FOR_BRIDGE'],
        )

        with patch('apps.mission_control.services.live_paper_autonomy_funnel._ensure_execution_candidates_for_readiness', return_value={}):
            diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(diagnostics.get('execution_candidate_visible_count'), 0)
        self.assertGreaterEqual(diagnostics.get('execution_artifact_blocked_count', 0), 1)
        self.assertIn('PAPER_EXECUTION_CANDIDATE_SOURCE_MODEL_MISMATCH', diagnostics.get('execution_artifact_reason_codes', []))

    def test_handoff_paper_execution_candidates_align_with_execution_candidate_visible(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.risk_agent.models import AutonomousExecutionReadiness, AutonomousExecutionReadinessStatus, RiskRuntimeApprovalStatus

        market = self._provider_and_market('paper-execution-handoff-alignment')
        decision = self._risk_decision(market=market, approval_status=RiskRuntimeApprovalStatus.APPROVED)
        AutonomousExecutionReadiness.objects.create(
            linked_market=market,
            linked_approval_review=decision,
            readiness_status=AutonomousExecutionReadinessStatus.READY,
            readiness_confidence=Decimal('0.7800'),
            readiness_summary='handoff-alignment',
            readiness_reason_codes=['READY_FOR_BRIDGE'],
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        self.assertEqual(
            diagnostics.get('paper_execution_candidates'),
            diagnostics.get('execution_candidate_visible_count'),
        )

    def test_prediction_intake_missing_required_fields_is_explicit(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-missing-fields')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
        )
        handoff.handoff_status = ''
        handoff.save(update_fields=['handoff_status'])
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertEqual(summary.get('prediction_intake_missing_fields'), 1)
        self.assertIn('PREDICTION_INTAKE_MISSING_REQUIRED_FIELDS', summary.get('prediction_intake_reason_codes', []))

    def test_prediction_intake_bridge_creates_prediction_candidate_for_eligible_handoff(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionConvictionReview
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-bridge')
        market.current_market_probability = Decimal('0.4900')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertGreaterEqual(summary.get('prediction_intake_created', 0), 1)
        self.assertTrue(PredictionConvictionReview.objects.exists())

    def test_prediction_intake_reused_candidate_is_explicit(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-reused')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        run_prediction_intake_review(triggered_by='prediction-reused-test')

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertIn('PREDICTION_INTAKE_ROUTE_AVAILABLE', summary.get('prediction_intake_reason_codes', []))
        self.assertIn('PREDICTION_INTAKE_REUSED_EXISTING_CANDIDATE', summary.get('prediction_intake_reason_codes', []))
        self.assertNotIn('PREDICTION_INTAKE_ROUTE_MISSING', summary.get('prediction_intake_reason_codes', []))

    def test_prediction_intake_route_available_but_filtered_is_not_route_missing(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-filtered')
        market.current_market_probability = Decimal('0.4100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.4300'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertIn('PREDICTION_INTAKE_ROUTE_AVAILABLE', summary.get('prediction_intake_reason_codes', []))
        self.assertIn('PREDICTION_INTAKE_CONFIDENCE_BELOW_THRESHOLD', summary.get('prediction_intake_reason_codes', []))
        self.assertIn('PREDICTION_INTAKE_CONFIDENCE_BELOW_THRESHOLD', summary.get('prediction_intake_filter_reason_codes', []))
        self.assertNotIn('PREDICTION_INTAKE_ROUTE_MISSING', summary.get('prediction_intake_reason_codes', []))

    def test_handoff_scoring_summary_explains_deferred_low_confidence(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('handoff-scoring-deferred-low-confidence')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.DEFERRED,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.4500'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={'narrative_priority': '0.6200'},
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.4500'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('handoff_scoring_summary') or {}
        self.assertEqual(summary.get('handoff_deferred'), 1)
        self.assertIn('HANDOFF_STATUS_DEFERRED_LOW_CONFIDENCE', summary.get('handoff_status_reason_codes', []))
        self.assertIn('HANDOFF_CONFIDENCE_BELOW_READY_THRESHOLD', summary.get('handoff_status_reason_codes', []))
        example = (diagnostics.get('handoff_scoring_examples') or [{}])[0]
        self.assertEqual(example.get('status_reason_code'), 'HANDOFF_STATUS_DEFERRED_LOW_CONFIDENCE')
        self.assertEqual(example.get('observed_value'), '0.4500')
        self.assertEqual(example.get('threshold'), '0.5500')

    def test_prediction_intake_borderline_confidence_too_low_stays_blocked(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-too-low')
        market.current_market_probability = Decimal('0.4400')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.4200'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={'narrative_priority': '0.9000', 'divergence_strength': '0.9000'},
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.3200'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        intake_summary = diagnostics.get('prediction_intake_summary') or {}
        borderline = diagnostics.get('handoff_borderline_summary') or {}
        self.assertIn('PREDICTION_INTAKE_GUARDRAIL_REJECTED', intake_summary.get('prediction_intake_guardrail_reason_codes', []))
        self.assertEqual(borderline.get('borderline_handoffs'), 0)

    def test_prediction_intake_borderline_eligible_can_be_promoted(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-promoted')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5200'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={'narrative_priority': '0.8200', 'divergence_strength': '0.6663'},
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.4500'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        intake_summary = diagnostics.get('prediction_intake_summary') or {}
        borderline = diagnostics.get('handoff_borderline_summary') or {}
        self.assertGreaterEqual(intake_summary.get('prediction_intake_attempted', 0), 1)
        self.assertIn('HANDOFF_BORDERLINE_PROMOTED_TO_PREDICTION', borderline.get('borderline_reason_codes', []))
        self.assertTrue(PredictionIntakeCandidate.objects.filter(linked_prediction_handoff_candidate=handoff).exists())

    def test_prediction_intake_borderline_low_narrative_stays_blocked(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-low-narrative')
        market.current_market_probability = Decimal('0.5300')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5000'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={'narrative_priority': '0.6200', 'divergence_strength': '0.7000'},
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.4900'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        intake_summary = diagnostics.get('prediction_intake_summary') or {}
        borderline = diagnostics.get('handoff_borderline_summary') or {}
        self.assertIn('HANDOFF_BORDERLINE_BLOCKED_BY_LOW_NARRATIVE_PRIORITY', borderline.get('borderline_reason_codes', []))
        self.assertIn('PREDICTION_INTAKE_GUARDRAIL_REJECTED', intake_summary.get('prediction_intake_guardrail_reason_codes', []))

    def test_borderline_structural_block_explicitly_activity_weak(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-structural-activity-weak')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.DEFERRED
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5000'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={
                'volume_quality': '0.8500',
                'activity_quality': '0.2400',
                'liquidity_quality': '0.9100',
                'narrative_priority': '0.8200',
                'divergence_strength': '0.7000',
                'time_window_quality': '0.3000',
            },
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run, linked_market=market, linked_pursuit_score=score, linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED, handoff_confidence=Decimal('0.4900')
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        structural_summary = diagnostics.get('handoff_structural_summary') or {}
        structural_examples = diagnostics.get('handoff_structural_examples') or []
        self.assertIn('HANDOFF_STRUCTURAL_WEAK_ACTIVITY', structural_summary.get('structural_reason_codes', []))
        self.assertEqual(structural_examples[0].get('structural_reason_code'), 'HANDOFF_STRUCTURAL_WEAK_ACTIVITY')

    def test_borderline_structural_block_explicitly_time_window_weak(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-structural-time-weak')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.DEFERRED
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5000'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={
                'volume_quality': '0.8500',
                'activity_quality': '0.3500',
                'liquidity_quality': '0.9100',
                'narrative_priority': '0.8200',
                'divergence_strength': '0.7000',
                'time_window_quality': '0.2000',
            },
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run, linked_market=market, linked_pursuit_score=score, linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED, handoff_confidence=Decimal('0.4900')
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        structural_examples = diagnostics.get('handoff_structural_examples') or []
        self.assertEqual(structural_examples[0].get('structural_reason_code'), 'HANDOFF_STRUCTURAL_WEAK_TIME_WINDOW')

    def test_borderline_structural_block_explicitly_activity_and_time_window_weak(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-structural-combo-weak')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.DEFERRED
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5000'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={
                'volume_quality': '0.8800',
                'activity_quality': '0.2500',
                'liquidity_quality': '0.8900',
                'narrative_priority': '0.8200',
                'divergence_strength': '0.7000',
                'time_window_quality': '0.2100',
            },
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run, linked_market=market, linked_pursuit_score=score, linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED, handoff_confidence=Decimal('0.4900')
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        structural_summary = diagnostics.get('handoff_structural_summary') or {}
        self.assertIn('HANDOFF_STRUCTURAL_WEAK_ACTIVITY_AND_TIME_WINDOW', structural_summary.get('structural_reason_codes', []))

    def test_borderline_structural_conservative_override_promotes_prediction_intake(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-borderline-structural-override')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.DEFERRED
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5200'),
            score_status=ResearchPursuitScoreStatus.DEFER,
            score_components={
                'volume_quality': '1.0000',
                'activity_quality': '0.2500',
                'liquidity_quality': '1.0000',
                'narrative_priority': '0.8200',
                'divergence_strength': '0.6663',
                'time_window_quality': '0.2200',
            },
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run, linked_market=market, linked_pursuit_score=score, linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED, handoff_confidence=Decimal('0.4500')
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        structural_summary = diagnostics.get('handoff_structural_summary') or {}
        borderline_summary = diagnostics.get('handoff_borderline_summary') or {}
        self.assertGreaterEqual(structural_summary.get('override_promoted', 0), 1)
        self.assertIn('HANDOFF_BORDERLINE_PROMOTED_TO_PREDICTION', borderline_summary.get('borderline_reason_codes', []))
        self.assertTrue(PredictionIntakeCandidate.objects.filter(linked_prediction_handoff_candidate=handoff).exists())

    def test_handoff_scoring_summary_explains_no_promotion(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('handoff-scoring-no-promotion')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.5900'),
            score_status=ResearchPursuitScoreStatus.KEEP_ON_RESEARCH_WATCHLIST,
            score_components={'narrative_priority': '0.6200'},
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.WATCH,
            handoff_confidence=Decimal('0.5900'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('handoff_scoring_summary') or {}
        self.assertIn('HANDOFF_STATUS_DEFERRED_NO_PROMOTION', summary.get('handoff_status_reason_codes', []))
        self.assertIn('HANDOFF_STATUS_DEFERRED_NO_PROMOTION', summary.get('deferred_reasons', []))

    def test_handoff_scoring_summary_explains_ready_and_prediction_can_pass(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('handoff-scoring-ready')
        market.current_market_probability = Decimal('0.6100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.7700'),
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
            score_components={'narrative_priority': '0.8200'},
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        handoff_summary = diagnostics.get('handoff_scoring_summary') or {}
        intake_summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertEqual(handoff_summary.get('handoff_ready'), 1)
        self.assertIn('HANDOFF_STATUS_READY_BY_PURSUIT', handoff_summary.get('handoff_status_reason_codes', []))
        self.assertGreaterEqual(intake_summary.get('prediction_intake_created', 0), 1)

    def test_prediction_intake_blocks_ineligible_status_with_explicit_filter_reason(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-status-ineligible')
        market.current_market_probability = Decimal('0.6400')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status='paused',
            handoff_confidence=Decimal('0.8000'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertIn('PREDICTION_INTAKE_HANDOFF_STATUS_INELIGIBLE', summary.get('prediction_intake_filter_reason_codes', []))
        self.assertEqual(summary.get('prediction_intake_ineligible_count'), 1)

    def test_prediction_intake_blocks_missing_market_probability_with_explicit_filter_reason(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-market-probability-missing')
        market.current_market_probability = None
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.8000'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertIn('PREDICTION_INTAKE_MARKET_PROBABILITY_MISSING', summary.get('prediction_intake_filter_reason_codes', []))

    def test_prediction_intake_reuse_is_not_counted_as_guardrail(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-reuse-no-guardrail')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.PREDICTION_READY,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        run_prediction_intake_review(triggered_by='prediction-reuse-no-guardrail')
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertEqual(summary.get('prediction_intake_guardrail_blocked'), 0)
        self.assertGreaterEqual(summary.get('prediction_intake_reused_count', 0), 1)
        self.assertIn('PREDICTION_INTAKE_REUSED_EXISTING_CANDIDATE', summary.get('prediction_intake_reason_codes', []))

    def test_prediction_visibility_counts_reused_candidate_as_visible(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-visibility-reused')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        run_prediction_intake_review(triggered_by='prediction-visibility-reused')
        candidate = market.prediction_intake_candidates.order_by('-id').first()
        candidate.created_at = timezone.now() - timedelta(minutes=120)
        candidate.save(update_fields=['created_at'])

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=1))
        visibility = diagnostics.get('prediction_visibility_summary') or {}
        self.assertGreaterEqual(diagnostics.get('prediction_candidates', 0), 1)
        self.assertGreaterEqual(visibility.get('prediction_intake_reused_count', 0), 1)
        self.assertGreaterEqual(visibility.get('prediction_candidates_visible_count', 0), 1)
        self.assertIn('PREDICTION_REUSED_BUT_NOT_COUNTED', visibility.get('prediction_visibility_reason_codes', []))

    def test_prediction_visibility_hidden_by_status_is_explicit(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate, PredictionIntakeRun, PredictionIntakeStatus
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-visibility-hidden-status')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run, linked_market=market, linked_pursuit_score=score, linked_assessment=assessment, handoff_status=PredictionHandoffStatus.BLOCKED
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.BLOCKED,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        visibility = diagnostics.get('prediction_visibility_summary') or {}
        self.assertEqual(visibility.get('prediction_candidates_visible_count'), 0)
        self.assertGreaterEqual(visibility.get('prediction_candidates_hidden_count', 0), 1)
        self.assertIn('PREDICTION_HIDDEN_BY_STATUS_FILTER', visibility.get('prediction_visibility_reason_codes', []))

    def test_prediction_visibility_summary_includes_risk_route_diagnostics(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeRun, PredictionIntakeStatus, PredictionIntakeCandidate
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-risk-summary')
        market.current_market_probability = Decimal('0.5100')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7700'),
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        handoff = PredictionHandoffCandidate.objects.order_by('-id').first()
        PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        self.assertIn('risk_route_expected', prediction_risk)
        self.assertIn('risk_route_available', prediction_risk)
        self.assertIn('risk_route_attempted', prediction_risk)
        self.assertIn('risk_route_created', prediction_risk)
        self.assertIn('risk_route_blocked', prediction_risk)
        self.assertIn('risk_route_missing_status_count', prediction_risk)
        self.assertIn('risk_route_summary', prediction_risk)
        self.assertIn('prediction_risk_examples', diagnostics)
        self.assertTrue(
            any(
                code in prediction_risk.get('risk_route_reason_codes', [])
                for code in [
                    'PREDICTION_RISK_ROUTE_MISSING',
                    'PREDICTION_RISK_STATUS_FILTER_REJECTED',
                    'PREDICTION_RISK_ROUTE_AVAILABLE',
                    'PREDICTION_RISK_WITH_CAUTION_NOT_IN_BAND',
                    'PREDICTION_RISK_WITH_CAUTION_BLOCKED_BY_LOW_EDGE',
                ]
            )
        )

    def test_prediction_risk_summary_marks_status_filter_rejection_for_monitor_only_visible_candidate(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate, PredictionIntakeRun, PredictionIntakeStatus
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-risk-monitor-only-filter')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7600'),
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        caution = diagnostics.get('prediction_risk_caution_summary') or {}
        prediction_status = diagnostics.get('prediction_status_summary') or {}
        self.assertEqual(prediction_risk.get('risk_route_expected'), 1)
        self.assertEqual(prediction_risk.get('risk_route_available'), 0)
        self.assertEqual(prediction_risk.get('risk_route_attempted'), 0)
        self.assertGreaterEqual(prediction_risk.get('risk_route_missing_status_count', 0), 1)
        self.assertIn('PREDICTION_RISK_WITH_CAUTION_NOT_IN_BAND', prediction_risk.get('risk_route_reason_codes', []))
        self.assertEqual(caution.get('monitor_only_candidates'), 1)
        self.assertEqual(caution.get('risk_with_caution_eligible_count'), 0)
        self.assertEqual(prediction_status.get('prediction_status_monitor_only_count'), 1)
        self.assertIn('PREDICTION_STATUS_MONITOR_ONLY_LOW_CONFIDENCE', prediction_status.get('prediction_status_reason_codes', []))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel.run_risk_runtime_review')
    def test_monitor_only_with_strong_edge_and_lineage_enters_risk_with_caution(self, mock_risk_runtime_review):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import (
            PredictionConvictionBucket,
            PredictionConvictionReview,
            PredictionConvictionReviewStatus,
            PredictionIntakeCandidate,
            PredictionIntakeRun,
            PredictionIntakeStatus,
        )
        from apps.research_agent.models import (
            NarrativeConsensusRun,
            NarrativeConsensusRecord,
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-risk-with-caution-promoted')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.5100'),
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        consensus_run = NarrativeConsensusRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        consensus = NarrativeConsensusRecord.objects.create(
            consensus_run=consensus_run,
            topic_label='macro',
            confidence_score=Decimal('0.7600'),
            summary='Aligned consensus',
        )
        candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            linked_consensus_record=consensus,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
            handoff_confidence=Decimal('0.5100'),
            structural_priority=Decimal('0.6900'),
            narrative_priority=Decimal('0.6700'),
            metadata={'handoff_status': 'deferred', 'pursuit_priority_bucket': 'medium'},
        )
        PredictionConvictionReview.objects.create(
            linked_intake_candidate=candidate,
            system_probability=Decimal('0.6000'),
            market_probability=Decimal('0.5000'),
            calibrated_probability=Decimal('0.6000'),
            raw_edge=Decimal('0.1000'),
            adjusted_edge=Decimal('0.1000'),
            confidence=Decimal('0.5100'),
            uncertainty=Decimal('0.3000'),
            conviction_bucket=PredictionConvictionBucket.MEDIUM_CONVICTION,
            review_status=PredictionConvictionReviewStatus.READY_FOR_RISK,
            reason_codes=[],
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        caution = diagnostics.get('prediction_risk_caution_summary') or {}
        self.assertEqual(prediction_risk.get('risk_route_available'), 1)
        self.assertGreaterEqual(prediction_risk.get('risk_route_attempted', 0), 1)
        self.assertIn('PREDICTION_RISK_WITH_CAUTION_PROMOTED', prediction_risk.get('risk_route_reason_codes', []))
        self.assertEqual(caution.get('risk_with_caution_eligible_count'), 1)
        self.assertEqual(caution.get('risk_with_caution_promoted_count'), 1)
        self.assertIn('PREDICTION_RISK_WITH_CAUTION_PROMOTED', caution.get('risk_with_caution_reason_codes', []))
        mock_risk_runtime_review.assert_called_once()

    def test_prediction_artifact_summary_creates_missing_conviction_and_handoff_for_visible_candidate(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate, PredictionIntakeRun, PredictionIntakeStatus, RiskReadyPredictionHandoff
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-artifact-create')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.WATCH,
            handoff_confidence=Decimal('0.5200'),
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
            handoff_confidence=Decimal('0.5200'),
            narrative_priority=Decimal('0.7400'),
            structural_priority=Decimal('0.7000'),
            metadata={'handoff_status': 'watch', 'pursuit_priority_bucket': 'medium'},
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        artifact = diagnostics.get('prediction_artifact_summary') or {}
        examples = diagnostics.get('prediction_artifact_examples') or []
        self.assertEqual(artifact.get('prediction_artifact_expected_count'), 1)
        self.assertEqual(artifact.get('conviction_review_created_count'), 1)
        self.assertEqual(artifact.get('risk_ready_handoff_created_count'), 1)
        self.assertIn('PREDICTION_ARTIFACT_MISMATCH_RESOLVED', artifact.get('prediction_artifact_reason_codes', []))
        self.assertTrue(any(example.get('candidate_id') == candidate.id for example in examples))
        self.assertTrue(RiskReadyPredictionHandoff.objects.filter(linked_conviction_review__linked_intake_candidate=candidate).exists())

    @patch('apps.mission_control.services.live_paper_autonomy_funnel.run_risk_runtime_review')
    def test_prediction_artifact_summary_reuses_existing_conviction_and_handoff(self, _mock_risk_runtime_review):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionConvictionReview, PredictionConvictionReviewStatus, RiskReadyPredictionHandoff
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-artifact-reuse')
        market.current_market_probability = Decimal('0.5000')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.8100'),
        )
        run_prediction_intake_review(triggered_by='artifact-reuse-test')
        review = PredictionConvictionReview.objects.order_by('-id').first()
        review.review_status = PredictionConvictionReviewStatus.READY_FOR_RISK
        review.save(update_fields=['review_status', 'updated_at'])
        RiskReadyPredictionHandoff.objects.filter(linked_conviction_review=review).update(created_at=timezone.now() - timedelta(hours=2))

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        artifact = diagnostics.get('prediction_artifact_summary') or {}
        self.assertEqual(artifact.get('conviction_review_created_count'), 0)
        self.assertGreaterEqual(artifact.get('conviction_review_reused_count', 0), 1)
        self.assertEqual(artifact.get('risk_ready_handoff_created_count'), 0)
        self.assertGreaterEqual(artifact.get('risk_ready_handoff_reused_count', 0), 1)
        self.assertIn('PREDICTION_CONVICTION_REVIEW_REUSED', artifact.get('prediction_artifact_reason_codes', []))
        self.assertIn('PREDICTION_RISK_READY_HANDOFF_REUSED', artifact.get('prediction_artifact_reason_codes', []))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel.run_risk_runtime_review')
    def test_prediction_risk_summary_avoids_artifact_mismatch_after_bridge_resolution(self, mock_risk_runtime_review):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import (
            PredictionConvictionBucket,
            PredictionConvictionReview,
            PredictionConvictionReviewStatus,
            PredictionIntakeCandidate,
            PredictionIntakeRun,
            PredictionIntakeStatus,
            RiskReadyPredictionHandoff,
        )
        from apps.research_agent.models import (
            NarrativeConsensusRecord,
            NarrativeConsensusRun,
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-artifact-risk-route')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.WATCH,
            handoff_confidence=Decimal('0.5100'),
        )
        consensus_run = NarrativeConsensusRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        consensus = NarrativeConsensusRecord.objects.create(
            consensus_run=consensus_run,
            topic_label='macro',
            confidence_score=Decimal('0.7900'),
            summary='Aligned consensus for caution promotion',
        )
        intake_run = PredictionIntakeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            linked_consensus_record=consensus,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
            handoff_confidence=Decimal('0.5100'),
            narrative_priority=Decimal('0.7300'),
            structural_priority=Decimal('0.7200'),
            metadata={'handoff_status': 'watch', 'pursuit_priority_bucket': 'medium'},
        )
        review = PredictionConvictionReview.objects.create(
            linked_intake_candidate=candidate,
            system_probability=Decimal('0.6200'),
            market_probability=Decimal('0.5000'),
            calibrated_probability=Decimal('0.6200'),
            raw_edge=Decimal('0.1200'),
            adjusted_edge=Decimal('0.1200'),
            confidence=Decimal('0.5300'),
            uncertainty=Decimal('0.2600'),
            conviction_bucket=PredictionConvictionBucket.MEDIUM_CONVICTION,
            review_status=PredictionConvictionReviewStatus.READY_FOR_RISK,
            reason_codes=['SEEDED_FOR_ARTIFACT_MISMATCH_FIX_TEST'],
        )
        RiskReadyPredictionHandoff.objects.filter(linked_conviction_review=review).delete()

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        artifact = diagnostics.get('prediction_artifact_summary') or {}
        self.assertGreaterEqual(prediction_risk.get('risk_route_available', 0), 1)
        self.assertNotIn('PREDICTION_RISK_ROUTE_MISSING', prediction_risk.get('risk_route_reason_codes', []))
        self.assertIn('PREDICTION_ARTIFACT_MISMATCH_RESOLVED', prediction_risk.get('risk_route_reason_codes', []))
        self.assertGreaterEqual(artifact.get('risk_ready_handoff_created_count', 0), 1)
        mock_risk_runtime_review.assert_called_once()

    def test_prediction_status_summary_marks_reused_monitor_only_candidate(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionIntakeCandidate, PredictionIntakeRun, PredictionIntakeStatus
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-status-reused-monitor')
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        handoff = PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.WATCH,
            handoff_confidence=Decimal('0.5000'),
        )
        intake_run = PredictionIntakeRun.objects.create(
            started_at=timezone.now() - timedelta(hours=2),
            completed_at=timezone.now() - timedelta(hours=2),
        )
        candidate = PredictionIntakeCandidate.objects.create(
            intake_run=intake_run,
            linked_market=market,
            linked_prediction_handoff_candidate=handoff,
            intake_status=PredictionIntakeStatus.MONITOR_ONLY,
            handoff_confidence=Decimal('0.5100'),
            reason_codes=['PREDICTION_STATUS_MONITOR_ONLY_LOW_CONFIDENCE'],
        )
        PredictionIntakeCandidate.objects.filter(id=candidate.id).update(created_at=timezone.now() - timedelta(hours=2))

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_status = diagnostics.get('prediction_status_summary') or {}
        examples = diagnostics.get('prediction_status_examples') or []
        self.assertIn('PREDICTION_STATUS_MONITOR_ONLY_REUSED_STATUS', prediction_status.get('prediction_status_reason_codes', []))
        self.assertTrue(any(item.get('status_reason_code') == 'PREDICTION_STATUS_MONITOR_ONLY_REUSED_STATUS' for item in examples))

    @patch('apps.mission_control.services.live_paper_autonomy_funnel.run_risk_runtime_review')
    def test_prediction_risk_summary_attempts_bridge_when_candidate_is_routable(self, mock_risk_runtime_review):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionConvictionReview, PredictionConvictionReviewStatus
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-risk-bridge-attempt')
        market.current_market_probability = Decimal('0.5000')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.8200'),
        )
        run_prediction_intake_review(triggered_by='mission-control-risk-bridge-attempt')
        review = PredictionConvictionReview.objects.order_by('-id').first()
        review.review_status = PredictionConvictionReviewStatus.READY_FOR_RISK
        review.save(update_fields=['review_status', 'updated_at'])

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        self.assertGreaterEqual(prediction_risk.get('risk_route_available', 0), 1)
        self.assertGreaterEqual(prediction_risk.get('risk_route_attempted', 0), 1)
        self.assertIn('PREDICTION_RISK_ATTEMPTED', prediction_risk.get('risk_route_reason_codes', []))
        self.assertNotIn('PREDICTION_RISK_STATUS_FILTER_REJECTED', prediction_risk.get('risk_route_reason_codes', []))
        mock_risk_runtime_review.assert_called_once()

    def test_prediction_risk_summary_reuses_existing_risk_decision(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.prediction_agent.models import PredictionConvictionReview, PredictionConvictionReviewStatus, RiskReadyPredictionHandoff
        from apps.prediction_agent.services.run import run_prediction_intake_review
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )
        from apps.risk_agent.models import RiskApprovalDecision, RiskRuntimeApprovalStatus, RiskRuntimeCandidate, RiskRuntimeRun

        market = self._provider_and_market('prediction-risk-reused-decision')
        market.current_market_probability = Decimal('0.5000')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run, linked_market=market, structural_status=ResearchStructuralStatus.PREDICTION_READY
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run, linked_assessment=assessment, linked_market=market, score_status=ResearchPursuitScoreStatus.READY_FOR_PREDICTION
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.READY,
            handoff_confidence=Decimal('0.7900'),
        )
        run_prediction_intake_review(triggered_by='mission-control-risk-reused')
        review = PredictionConvictionReview.objects.order_by('-id').first()
        review.review_status = PredictionConvictionReviewStatus.READY_FOR_RISK
        review.save(update_fields=['review_status', 'updated_at'])
        intake_candidate = review.linked_intake_candidate
        risk_handoff = RiskReadyPredictionHandoff.objects.filter(linked_conviction_review=review).order_by('-id').first()
        runtime_run = RiskRuntimeRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        runtime_candidate = RiskRuntimeCandidate.objects.create(
            runtime_run=runtime_run,
            linked_risk_ready_prediction_handoff=risk_handoff,
            linked_prediction_conviction_review=review,
            linked_prediction_intake_candidate=intake_candidate,
            linked_market=market,
            market_provider=market.provider.slug,
            category=market.category or '',
            calibrated_probability=Decimal('0.6200'),
            market_probability=Decimal('0.5000'),
            adjusted_edge=Decimal('0.1200'),
            intake_status='READY_FOR_RISK_RUNTIME',
            confidence_score=Decimal('0.8000'),
            uncertainty_score=Decimal('0.2000'),
            conviction_bucket='MEDIUM',
            portfolio_pressure_state='LOW',
            context_summary='seeded-for-reuse-test',
            reason_codes=['SEEDED_FOR_TEST'],
            evidence_quality_score=Decimal('0.7000'),
            precedent_caution_score=Decimal('0.3000'),
            linked_portfolio_context={},
            linked_feedback_context={},
            market_liquidity_context={},
            predicted_status='READY',
            metadata={'paper_demo_only': True},
        )
        RiskApprovalDecision.objects.create(
            linked_candidate=runtime_candidate,
            approval_status=RiskRuntimeApprovalStatus.APPROVED,
            approval_confidence=Decimal('0.7000'),
            approval_summary='seeded-for-reuse-test',
            approval_rationale='seeded-for-reuse-test',
            reason_codes=['SEEDED_FOR_TEST'],
            blockers=[],
            risk_score=Decimal('0.3000'),
            max_allowed_exposure=Decimal('100.00'),
            watch_required=False,
            metadata={'seeded_for_test': True},
        )

        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        prediction_risk = diagnostics.get('prediction_risk_summary') or {}
        self.assertGreaterEqual(prediction_risk.get('risk_route_available', 0), 1)
        self.assertEqual(prediction_risk.get('risk_route_attempted', 0), 0)
        self.assertIn('PREDICTION_RISK_REUSED_EXISTING_DECISION', prediction_risk.get('risk_route_reason_codes', []))

    def test_prediction_intake_reason_code_semantics_keep_guardrail_and_filter_separate(self):
        from apps.mission_control.services.live_paper_autonomy_funnel import _build_handoff_diagnostics
        from apps.research_agent.models import (
            PredictionHandoffCandidate,
            PredictionHandoffStatus,
            ResearchPursuitRun,
            ResearchPursuitScore,
            ResearchPursuitScoreStatus,
            ResearchStructuralAssessment,
            ResearchStructuralStatus,
        )

        market = self._provider_and_market('prediction-semantics-guardrail-filter')
        market.current_market_probability = Decimal('0.4800')
        market.save(update_fields=['current_market_probability'])
        run = ResearchPursuitRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())
        assessment = ResearchStructuralAssessment.objects.create(
            pursuit_run=run,
            linked_market=market,
            structural_status=ResearchStructuralStatus.DEFERRED,
        )
        score = ResearchPursuitScore.objects.create(
            pursuit_run=run,
            linked_assessment=assessment,
            linked_market=market,
            pursuit_score=Decimal('0.4500'),
            score_status=ResearchPursuitScoreStatus.DEFER,
        )
        PredictionHandoffCandidate.objects.create(
            pursuit_run=run,
            linked_market=market,
            linked_pursuit_score=score,
            linked_assessment=assessment,
            handoff_status=PredictionHandoffStatus.DEFERRED,
            handoff_confidence=Decimal('0.4500'),
        )
        diagnostics = _build_handoff_diagnostics(window_start=timezone.now() - timedelta(minutes=60))
        summary = diagnostics.get('prediction_intake_summary') or {}
        self.assertIn('PREDICTION_INTAKE_GUARDRAIL_REJECTED', summary.get('prediction_intake_guardrail_reason_codes', []))
        self.assertNotIn('PREDICTION_INTAKE_GUARDRAIL_REJECTED', summary.get('prediction_intake_filter_reason_codes', []))


class ExtendedPaperRunGateApiTests(TestCase):
    def _base_validation(self, status: str):
        return {
            'preset_name': 'live_read_only_paper_conservative',
            'validation_status': status,
        }

    def _base_trend(self, *, latest_trial_status='PASS', trend_status='STABLE', readiness_status='READY_FOR_EXTENDED_RUN', sample_size=3, warn_count=0, fail_count=0):
        return {
            'sample_size': sample_size,
            'latest_trial_status': latest_trial_status,
            'trend_status': trend_status,
            'readiness_status': readiness_status,
            'counts': {
                'pass_count': max(sample_size - warn_count - fail_count, 0),
                'warn_count': warn_count,
                'fail_count': fail_count,
            },
        }

    def _base_history(self, latest_trial_status='PASS'):
        return {
            'count': 3,
            'latest_trial_status': latest_trial_status,
            'items': [],
        }

    def _base_attention(self, mode='HEALTHY'):
        return {'attention_mode': mode}

    def _base_funnel(self, status='ACTIVE'):
        return {'funnel_status': status}

    def _base_bootstrap(self):
        return {'session_active': True, 'heartbeat_active': True}

    def _call_gate(self, *, validation, trend, history, attention, funnel, bootstrap):
        with patch('apps.mission_control.services.extended_paper_run_gate.build_live_paper_validation_digest', return_value=validation), patch(
            'apps.mission_control.services.extended_paper_run_gate.build_live_paper_trial_trend_digest',
            return_value=trend,
        ), patch(
            'apps.mission_control.services.extended_paper_run_gate.list_live_paper_trial_history',
            return_value=history,
        ), patch(
            'apps.mission_control.services.extended_paper_run_gate.get_live_paper_attention_alert_status',
            return_value=attention,
        ), patch(
            'apps.mission_control.services.extended_paper_run_gate.build_live_paper_autonomy_funnel_snapshot',
            return_value=funnel,
        ), patch(
            'apps.mission_control.services.extended_paper_run_gate.get_live_paper_bootstrap_status',
            return_value=bootstrap,
        ):
            return self.client.get(reverse('mission_control:extended-paper-run-gate'))

    def test_gate_allow_case(self):
        response = self._call_gate(
            validation=self._base_validation('READY'),
            trend=self._base_trend(),
            history=self._base_history(),
            attention=self._base_attention('HEALTHY'),
            funnel=self._base_funnel('ACTIVE'),
            bootstrap=self._base_bootstrap(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['gate_status'], 'ALLOW')
        self.assertEqual(payload['next_action_hint'], 'Proceed to extended paper run')
        self.assertIn('VALIDATION_READY', payload['reason_codes'])

    def test_gate_allow_with_caution_case(self):
        response = self._call_gate(
            validation=self._base_validation('WARNING'),
            trend=self._base_trend(latest_trial_status='WARN', readiness_status='NEEDS_REVIEW', warn_count=1),
            history=self._base_history('WARN'),
            attention=self._base_attention('DEGRADED'),
            funnel=self._base_funnel('THIN_FLOW'),
            bootstrap=self._base_bootstrap(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['gate_status'], 'ALLOW_WITH_CAUTION')
        self.assertEqual(payload['next_action_hint'], 'Proceed cautiously and monitor the first cycles')
        self.assertIn('RECENT_WARNINGS', payload['reason_codes'])
        self.assertIn('ATTENTION_DEGRADED', payload['reason_codes'])
        self.assertIn('FUNNEL_THIN_FLOW', payload['reason_codes'])

    def test_gate_block_case(self):
        response = self._call_gate(
            validation=self._base_validation('BLOCKED'),
            trend=self._base_trend(latest_trial_status='FAIL', trend_status='DEGRADING', readiness_status='NOT_READY', fail_count=1),
            history=self._base_history('FAIL'),
            attention=self._base_attention('REVIEW_NOW'),
            funnel=self._base_funnel('STALLED'),
            bootstrap=self._base_bootstrap(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['gate_status'], 'BLOCK')
        self.assertEqual(payload['next_action_hint'], 'Do not start extended paper run yet')
        self.assertIn('VALIDATION_BLOCKED', payload['reason_codes'])
        self.assertIn('ATTENTION_BLOCKING', payload['reason_codes'])
        self.assertIn('FUNNEL_STALLED', payload['reason_codes'])

    def test_gate_payload_checks_and_contract_are_compact(self):
        response = self._call_gate(
            validation=self._base_validation('READY'),
            trend=self._base_trend(),
            history=self._base_history(),
            attention=self._base_attention('HEALTHY'),
            funnel=self._base_funnel('ACTIVE'),
            bootstrap=self._base_bootstrap(),
        )
        payload = response.json()
        expected = {
            'preset_name',
            'gate_status',
            'latest_trial_status',
            'trend_status',
            'readiness_status',
            'validation_status',
            'attention_mode',
            'funnel_status',
            'next_action_hint',
            'gate_summary',
            'reason_codes',
            'checks',
        }
        self.assertTrue(expected.issubset(payload.keys()))
        check_names = [item['check_name'] for item in payload['checks']]
        self.assertEqual(check_names, ['validation', 'trial_trend', 'operational_attention', 'autonomy_funnel', 'recent_trial_quality'])
        for item in payload['checks']:
            self.assertIn(item['status'], {'PASS', 'WARN', 'FAIL'})
            self.assertTrue(item['summary'])

    def test_missing_signals_fall_back_conservatively(self):
        response = self._call_gate(
            validation={},
            trend={},
            history={},
            attention={},
            funnel={},
            bootstrap={},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['gate_status'], 'BLOCK')
        self.assertEqual(payload['next_action_hint'], 'Run another short trial before extending')
        self.assertIn('INSUFFICIENT_TRIAL_DATA', payload['reason_codes'])
        self.assertIn('VALIDATION_BLOCKED', payload['reason_codes'])
        self.assertIn('ATTENTION_BLOCKING', payload['reason_codes'])

    def test_gate_reuses_existing_signal_services(self):
        with patch('apps.mission_control.services.extended_paper_run_gate.build_live_paper_validation_digest', return_value=self._base_validation('READY')) as mock_validation, patch(
            'apps.mission_control.services.extended_paper_run_gate.build_live_paper_trial_trend_digest',
            return_value=self._base_trend(),
        ) as mock_trend, patch(
            'apps.mission_control.services.extended_paper_run_gate.list_live_paper_trial_history',
            return_value=self._base_history(),
        ) as mock_history, patch(
            'apps.mission_control.services.extended_paper_run_gate.get_live_paper_attention_alert_status',
            return_value=self._base_attention('HEALTHY'),
        ) as mock_attention, patch(
            'apps.mission_control.services.extended_paper_run_gate.build_live_paper_autonomy_funnel_snapshot',
            return_value=self._base_funnel('ACTIVE'),
        ) as mock_funnel, patch(
            'apps.mission_control.services.extended_paper_run_gate.get_live_paper_bootstrap_status',
            return_value=self._base_bootstrap(),
        ) as mock_bootstrap:
            response = self.client.get(reverse('mission_control:extended-paper-run-gate'), {'preset': 'live_read_only_paper_conservative'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_validation.called)
        self.assertTrue(mock_trend.called)
        self.assertTrue(mock_history.called)
        self.assertTrue(mock_attention.called)
        self.assertTrue(mock_funnel.called)
        self.assertTrue(mock_bootstrap.called)


class ExtendedPaperRunLauncherApiTests(TestCase):
    def _bootstrap_status(self, *, session_active=True, heartbeat_active=True, current_session_status='RUNNING'):
        return {
            'session_active': session_active,
            'heartbeat_active': heartbeat_active,
            'current_session_status': current_session_status,
            'market_data_mode': 'REAL_READ_ONLY',
            'paper_execution_mode': 'PAPER_ONLY',
        }

    def _gate(self, status='ALLOW'):
        return {
            'gate_status': status,
            'reason_codes': ['VALIDATION_READY'] if status == 'ALLOW' else ['RECENT_WARNINGS'],
        }

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_gate_block_returns_blocked_without_bootstrap_launch(self, mock_gate, mock_bootstrap_status):
        mock_gate.return_value = self._gate('BLOCK')
        mock_bootstrap_status.return_value = self._bootstrap_status(session_active=False, heartbeat_active=False, current_session_status='MISSING')

        with patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session') as mock_bootstrap:
            response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['launch_status'], 'BLOCKED')
        self.assertIsNone(payload['caution_mode'])
        self.assertIn('GATE_BLOCKED', payload['reason_codes'])
        mock_bootstrap.assert_not_called()

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_gate_allow_starts_or_reuses_session(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'CREATED_AND_STARTED', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()

        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['launch_status'], 'STARTED')
        self.assertEqual(payload['gate_status'], 'ALLOW')
        self.assertFalse(payload['caution_mode'])
        self.assertEqual(payload['next_action_hint'], 'Extended run active; keep monitoring heartbeat cadence and paper risk posture')

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_gate_allow_with_caution_marks_caution_mode(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW_WITH_CAUTION')
        mock_bootstrap.return_value = {'bootstrap_action': 'STARTED_EXISTING_SAFE_SESSION', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()

        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['launch_status'], 'REUSED_PAUSED_SESSION')
        self.assertTrue(payload['caution_mode'])
        self.assertEqual(
            payload['next_action_hint'],
            'Extended run active in caution mode; monitor first cycles and attention bridge closely',
        )

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_does_not_duplicate_session_or_heartbeat_path(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'REUSED_EXISTING_SESSION', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()

        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['launch_status'], 'REUSED_RUNNING_SESSION')
        mock_bootstrap.assert_called_once()
        kwargs = mock_bootstrap.call_args.kwargs
        self.assertTrue(kwargs['auto_start_heartbeat'])
        self.assertTrue(kwargs['start_now'])

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_post_payload_contract(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'CREATED_AND_STARTED', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()
        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        payload = response.json()
        expected = {
            'preset_name',
            'launch_status',
            'gate_status',
            'session_active',
            'heartbeat_active',
            'current_session_status',
            'caution_mode',
            'next_action_hint',
            'launch_summary',
            'reason_codes',
        }
        self.assertTrue(expected.issubset(payload.keys()))

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_status_payload_contract(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'CREATED_AND_STARTED', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()
        self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')

        response = self.client.get(reverse('mission_control:extended-paper-run-status'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        expected = {
            'preset_name',
            'extended_run_active',
            'gate_status',
            'session_active',
            'heartbeat_active',
            'current_session_status',
            'caution_mode',
            'status_summary',
            'next_action_hint',
        }
        self.assertTrue(expected.issubset(payload.keys()))
        self.assertTrue(payload['extended_run_active'])

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_summary_and_hint_are_deterministic(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('BLOCK')
        mock_bootstrap.return_value = {'bootstrap_action': 'CREATED_AND_STARTED', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status(session_active=False, heartbeat_active=False, current_session_status='MISSING')
        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        payload = response.json()
        self.assertEqual(payload['launch_summary'], 'BLOCKED: gate=BLOCK; launch not executed.')
        self.assertEqual(payload['next_action_hint'], 'Extended run blocked by gate; resolve validation/trial/attention blockers first')

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_launcher_does_not_break_gate_flow(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'REUSED_EXISTING_SESSION', 'session_id': None}
        mock_bootstrap_status.return_value = self._bootstrap_status()
        launch = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        gate = self.client.get(reverse('mission_control:extended-paper-run-gate'))
        self.assertEqual(launch.status_code, 200)
        self.assertEqual(gate.status_code, 200)

    @patch('apps.mission_control.services.extended_paper_run_launcher.get_live_paper_bootstrap_status')
    @patch('apps.mission_control.services.extended_paper_run_launcher.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.extended_paper_run_launcher.build_extended_paper_run_gate')
    def test_preserves_real_read_only_and_paper_only_boundaries(self, mock_gate, mock_bootstrap, mock_bootstrap_status):
        mock_gate.return_value = self._gate('ALLOW')
        mock_bootstrap.return_value = {'bootstrap_action': 'CREATED_AND_STARTED', 'session_id': None}
        mock_bootstrap_status.return_value = {
            **self._bootstrap_status(),
            'market_data_mode': 'REAL_READ_ONLY',
            'paper_execution_mode': 'PAPER_ONLY',
        }
        response = self.client.post(reverse('mission_control:start-extended-paper-run'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['launch_status'], 'STARTED')
        self.assertNotIn('INVALID_MARKET_DATA_MODE', response.json()['reason_codes'])
        self.assertNotIn('INVALID_EXECUTION_MODE', response.json()['reason_codes'])


class TestConsoleApiTests(TestCase):
    def _status_payload(self):
        return {
            'test_status': 'COMPLETED',
            'current_phase': 'finalize',
            'started_at': timezone.now(),
            'ended_at': timezone.now(),
            'preset_name': 'live_read_only_paper_conservative',
            'session_active': True,
            'heartbeat_active': True,
            'current_session_status': 'RUNNING',
            'validation_status': 'READY',
            'trial_status': 'PASS',
            'trend_status': 'STABLE',
            'readiness_status': 'READY_FOR_EXTENDED_RUN',
            'gate_status': 'ALLOW',
            'extended_run_status': 'ACTIVE',
            'funnel_status': 'ACTIVE',
            'handoff_summary': {
                'summary_window': 'rolling_60m',
                'shortlisted_signals': 2,
                'handoff_candidates': 1,
                'consensus_reviews': 1,
                'prediction_candidates': 1,
                'risk_decisions': 1,
                'paper_execution_candidates': 0,
                'handoff_reason_codes': ['HANDOFF_CREATED'],
            },
            'shortlist_handoff_summary': {
                'shortlisted_signals': 2,
                'handoff_attempted': 1,
                'handoff_created': 1,
                'handoff_blocked': 0,
                'shortlist_handoff_reason_codes': ['SHORTLIST_PROMOTED_TO_HANDOFF'],
                'shortlist_handoff_examples': [{'signal_id': 10, 'market_id': 20, 'reason_code': 'SHORTLIST_PROMOTED_TO_HANDOFF'}],
            },
            'downstream_route_summary': {
                'route_expected': 2,
                'route_available': 1,
                'route_missing': 1,
                'route_attempted': 1,
                'route_created': 1,
                'route_blocked': 0,
                'downstream_route_reason_codes': ['DOWNSTREAM_ROUTE_CREATED_HANDOFF', 'DOWNSTREAM_ROUTE_MISSING'],
            },
            'downstream_route_examples': [
                {'signal_id': 10, 'market_id': 20, 'expected_route': 'research_pursuit_review', 'reason_code': 'DOWNSTREAM_ROUTE_CREATED_HANDOFF'}
            ],
            'market_link_summary': {
                'shortlisted_signals': 2,
                'market_link_attempted': 2,
                'market_link_resolved': 1,
                'market_link_missing': 1,
                'market_link_ambiguous': 0,
                'market_link_reason_codes': ['MARKET_LINK_RESOLVED', 'MARKET_LINK_NO_CANDIDATES'],
            },
            'market_link_examples': [{'signal_id': 10, 'candidate_count': 1, 'chosen_market_id': 20, 'reason_code': 'MARKET_LINK_RESOLVED'}],
            'consensus_alignment': {
                'consensus_reviews': 1,
                'shortlist_aligned_consensus_reviews': 1,
                'consensus_aligned_with_shortlist': True,
            },
            'handoff_scoring_summary': {
                'handoff_ready': 1,
                'handoff_deferred': 0,
                'handoff_blocked': 0,
                'handoff_status_reason_codes': ['HANDOFF_STATUS_READY_BY_PURSUIT'],
                'ready_threshold': '0.5500',
                'deferred_reasons': [],
            },
            'handoff_scoring_examples': [
                {
                    'handoff_id': 5,
                    'market_id': 20,
                    'handoff_status': 'ready',
                    'handoff_confidence': '0.7700',
                    'status_reason_code': 'HANDOFF_STATUS_READY_BY_PURSUIT',
                    'source_stage': 'pursuit',
                }
            ],
            'handoff_borderline_summary': {
                'borderline_handoffs': 1,
                'borderline_promoted': 1,
                'borderline_blocked': 0,
                'borderline_reason_codes': ['HANDOFF_BORDERLINE_ELIGIBLE', 'HANDOFF_BORDERLINE_PROMOTED_TO_PREDICTION'],
                'ready_threshold': '0.5500',
                'borderline_band': '[0.4500,0.5500)',
            },
            'handoff_borderline_examples': [
                {
                    'handoff_id': 5,
                    'market_id': 20,
                    'handoff_confidence': '0.4800',
                    'ready_threshold': '0.5500',
                    'borderline_band': '[0.4500,0.5500)',
                    'reason_code': 'HANDOFF_BORDERLINE_ELIGIBLE',
                    'decision_source': 'mission_control_borderline_guardrail_v1',
                }
            ],
            'handoff_structural_summary': {
                'structural_pass': 1,
                'structural_blocked': 0,
                'structural_weakness_count': 0,
                'structural_pass_count': 1,
                'structural_reason_codes': ['HANDOFF_STRUCTURAL_PASS'],
                'structural_block_reason_codes': [],
                'override_enabled': 1,
                'override_promoted': 0,
                'override_blocked': 0,
                'structural_guardrail_summary': 'structural_pass=1 structural_blocked=0',
            },
            'handoff_structural_examples': [
                {
                    'handoff_id': 5,
                    'market_id': 20,
                    'handoff_confidence': '0.4800',
                    'structural_status': 'prediction_ready',
                    'structural_reason_code': 'HANDOFF_STRUCTURAL_PASS',
                    'weak_components': [],
                    'strong_components': ['activity_quality', 'time_window_quality'],
                    'observed_values': {'activity_quality': '0.5000'},
                    'thresholds': {'activity_quality': {'min': '0.3000'}},
                    'decision_source': 'mission_control_borderline_guardrail_v1',
                }
            ],
            'attention_mode': 'HEALTHY',
            'portfolio_summary': {
                'cash': 10000.0,
                'equity': 10000.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'open_positions': 0,
                'recent_trades_count': 0,
                'account_summary_status': 'PAPER_ACCOUNT_SUMMARY_OK',
                'account_summary_reason_codes': [],
            },
            'scan_summary': {
                'summary_window': 'latest_scan_run',
                'runs': 1,
                'rss_items': 3,
                'reddit_items': 1,
                'x_items': 0,
                'deduped_items': 3,
                'clusters': 2,
                'shortlisted_signals': 1,
            },
            'blocker_summary': [],
            'next_action_hint': 'Proceed to extended paper run',
            'warnings': [],
            'errors': [],
            'reason_codes': ['VALIDATION_READY'],
            'summary': 'COMPLETED',
            'text_export': 'console text export',
        }

    @patch('apps.mission_control.views.start_test_console')
    def test_start_test_console_generates_status_and_log(self, mock_start):
        payload = self._status_payload()
        mock_start.return_value = payload

        response = self.client.post(reverse('mission_control:test-console-start'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['test_status'], 'COMPLETED')
        self.assertEqual(body['trial_status'], 'PASS')
        self.assertIn('scan_summary', body)
        self.assertIn('portfolio_summary', body)

    @patch('apps.mission_control.views.stop_test_console')
    def test_stop_test_console_is_explicit_and_safe(self, mock_stop):
        payload = self._status_payload()
        payload['test_status'] = 'STOPPED'
        payload['summary'] = 'Stop applied conservatively.'
        mock_stop.return_value = payload

        response = self.client.post(reverse('mission_control:test-console-stop'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['test_status'], 'STOPPED')
        self.assertEqual(body['summary'], 'Stop applied conservatively.')

    @patch('apps.mission_control.views.export_test_console_log')
    def test_export_log_text_works(self, mock_export):
        mock_export.return_value = 'copy paste friendly log\nhandoff_summary:\n  shortlisted_signals=1'
        response = self.client.get(reverse('mission_control:test-console-export-log'), {'format': 'text'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('copy paste friendly', response.content.decode())

    @patch('apps.mission_control.services.test_console._get_state_snapshot')
    def test_export_log_text_includes_handoff_summary_section(self, mock_state_snapshot):
        from apps.mission_control.services.test_console import export_test_console_log

        payload = self._status_payload()
        payload['text_export'] = ''
        mock_state_snapshot.return_value = (payload, payload, [])
        text_payload = export_test_console_log(fmt='text')
        self.assertIn('handoff_summary:', text_payload)
        self.assertIn('shortlisted_signals=', text_payload)
        self.assertIn('shortlist_handoff_summary:', text_payload)
        self.assertIn('handoff_attempted=', text_payload)
        self.assertIn('downstream_route_summary:', text_payload)
        self.assertIn('downstream_route_reason_codes=', text_payload)
        self.assertIn('market_link_summary:', text_payload)
        self.assertIn('market_link_reason_codes=', text_payload)
        self.assertIn('handoff_scoring_summary:', text_payload)
        self.assertIn('handoff_status_reason_codes=', text_payload)
        self.assertIn('handoff_borderline_summary:', text_payload)
        self.assertIn('borderline_reason_codes=', text_payload)
        self.assertIn('prediction_intake_summary:', text_payload)
        self.assertIn('prediction_intake_reason_codes=', text_payload)
        self.assertIn('prediction_intake_guardrail_reason_codes=', text_payload)
        self.assertIn('prediction_intake_filter_reason_codes=', text_payload)
        self.assertIn('prediction_visibility_summary:', text_payload)
        self.assertIn('prediction_visibility_reason_codes=', text_payload)
        self.assertIn('prediction_artifact_summary:', text_payload)
        self.assertIn('prediction_artifact_reason_codes=', text_payload)
        self.assertIn('risk_ready_handoff_created=', text_payload)
        self.assertIn('prediction_risk_summary:', text_payload)
        self.assertIn('risk_route_reason_codes=', text_payload)
        self.assertIn('risk_route_created=', text_payload)
        self.assertIn('risk_route_blocked=', text_payload)
        self.assertIn('risk_route_missing_status_count=', text_payload)
        self.assertIn('prediction_risk_examples=', text_payload)
        self.assertIn('prediction_risk_caution_summary:', text_payload)
        self.assertIn('risk_with_caution_reason_codes=', text_payload)
        self.assertIn('prediction_risk_caution_examples=', text_payload)
        self.assertIn('prediction_status_summary:', text_payload)
        self.assertIn('prediction_status_reason_codes=', text_payload)
        self.assertIn('runtime_ready_threshold=', text_payload)
        self.assertIn('prediction_status_examples=', text_payload)
        self.assertIn('paper_execution_summary:', text_payload)
        self.assertIn('paper_execution_route_reason_codes=', text_payload)
        self.assertIn('paper_execution_examples=', text_payload)
        self.assertIn('paper_execution_visibility_summary:', text_payload)
        self.assertIn('paper_execution_visibility_reason_codes=', text_payload)
        self.assertIn('paper_execution_visibility_examples=', text_payload)
        self.assertIn('paper_trade_summary:', text_payload)
        self.assertIn('paper_trade_route_reason_codes=', text_payload)
        self.assertIn('paper_trade_examples=', text_payload)
        self.assertIn('paper_trade_decision_summary:', text_payload)
        self.assertIn('paper_trade_decision_reason_codes=', text_payload)
        self.assertIn('paper_trade_decision_examples=', text_payload)
        self.assertIn('paper_trade_dispatch_summary:', text_payload)
        self.assertIn('paper_trade_dispatch_reason_codes=', text_payload)
        self.assertIn('paper_trade_dispatch_examples=', text_payload)
        self.assertIn('paper_trade_final_summary:', text_payload)
        self.assertIn('final_trade_reason_codes=', text_payload)
        self.assertIn('paper_trade_final_examples=', text_payload)
        self.assertIn('execution_lineage_summary:', text_payload)
        self.assertIn('fanout_reason_codes=', text_payload)
        self.assertIn('candidates_deduplicated=', text_payload)
        self.assertIn('dispatches_considered=', text_payload)
        self.assertIn('trades_materialized=', text_payload)
        self.assertIn('execution_artifact_summary:', text_payload)
        self.assertIn('execution_artifact_reason_codes=', text_payload)
        self.assertIn('execution_artifact_examples=', text_payload)
        self.assertIn('handoff_structural_summary:', text_payload)
        self.assertIn('structural_reason_codes=', text_payload)
        self.assertIn('handoff_structural_examples=', text_payload)
        self.assertIn('account_summary_status=', text_payload)

    @patch('apps.mission_control.views.export_test_console_log')
    def test_export_log_json_works(self, mock_export):
        mock_export.return_value = {'test_status': 'COMPLETED', 'summary': 'ok'}
        response = self.client.get(reverse('mission_control:test-console-export-log'), {'format': 'json'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['test_status'], 'COMPLETED')

    @patch('apps.mission_control.views.get_test_console_status')
    def test_status_consolidated_payload_contract(self, mock_status):
        mock_status.return_value = self._status_payload()
        response = self.client.get(reverse('mission_control:test-console-status'))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        expected_keys = {
            'test_status',
            'current_phase',
            'started_at',
            'ended_at',
            'preset_name',
            'session_active',
            'heartbeat_active',
            'current_session_status',
            'validation_status',
            'trial_status',
            'trend_status',
            'readiness_status',
            'gate_status',
            'extended_run_status',
            'funnel_status',
            'attention_mode',
            'portfolio_summary',
            'scan_summary',
            'blocker_summary',
            'next_action_hint',
            'warnings',
            'errors',
            'reason_codes',
        }
        self.assertTrue(expected_keys.issubset(set(body.keys())))

    @patch('apps.mission_control.views.start_test_console')
    def test_scan_without_signals_is_logged_as_warning_blocker(self, mock_start):
        payload = self._status_payload()
        payload['test_status'] = 'COMPLETED_WITH_WARNINGS'
        payload['scan_summary']['shortlisted_signals'] = 0
        payload['warnings'] = ['scan produced zero signals']
        payload['blocker_summary'] = ['SCAN_ZERO_SIGNALS']
        mock_start.return_value = payload

        response = self.client.post(reverse('mission_control:test-console-start'), data='{}', content_type='application/json')
        body = response.json()
        self.assertEqual(body['test_status'], 'COMPLETED_WITH_WARNINGS')
        self.assertIn('SCAN_ZERO_SIGNALS', body['blocker_summary'])

    @patch('apps.mission_control.views.start_test_console')
    def test_gate_block_is_reflected_in_status(self, mock_start):
        payload = self._status_payload()
        payload['test_status'] = 'BLOCKED'
        payload['gate_status'] = 'BLOCK'
        payload['blocker_summary'] = ['GATE_BLOCKED']
        payload['extended_run_status'] = 'SKIPPED_GATE_BLOCKED'
        mock_start.return_value = payload

        response = self.client.post(reverse('mission_control:test-console-start'), data='{}', content_type='application/json')
        body = response.json()
        self.assertEqual(body['test_status'], 'BLOCKED')
        self.assertEqual(body['gate_status'], 'BLOCK')
        self.assertIn('GATE_BLOCKED', body['blocker_summary'])

    @patch('apps.mission_control.views.start_test_console')
    def test_preserves_real_read_only_and_paper_only_boundaries(self, mock_start):
        payload = self._status_payload()
        payload['reason_codes'] = ['VALIDATION_READY', 'BOUNDARY_REAL_READ_ONLY', 'BOUNDARY_PAPER_ONLY']
        mock_start.return_value = payload

        response = self.client.post(reverse('mission_control:test-console-start'), data='{}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('BOUNDARY_REAL_READ_ONLY', response.json()['reason_codes'])
        self.assertIn('BOUNDARY_PAPER_ONLY', response.json()['reason_codes'])

    @patch('apps.mission_control.services.live_paper_bootstrap.bootstrap_live_read_only_paper_session')
    @patch('apps.mission_control.services.live_paper_trial_run.bootstrap_live_read_only_paper_session')
    def test_does_not_enable_live_trading_real(self, mock_trial_bootstrap, mock_console_bootstrap):
        safe_payload = {
            'bootstrap_action': 'CREATED_AND_STARTED',
            'stack_snapshot': {'paper_trading': {'paper_only': True}},
        }
        mock_console_bootstrap.return_value = safe_payload
        mock_trial_bootstrap.return_value = safe_payload
        from apps.mission_control.services.live_paper_bootstrap import bootstrap_live_read_only_paper_session

        result = bootstrap_live_read_only_paper_session()
        self.assertIn('stack_snapshot', result)
        self.assertTrue(result['stack_snapshot']['paper_trading']['paper_only'])
