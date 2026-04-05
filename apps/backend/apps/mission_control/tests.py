from unittest.mock import patch
import json
from datetime import timedelta

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
