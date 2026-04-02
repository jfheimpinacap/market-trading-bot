from unittest.mock import patch
import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousProfileSwitchRecord,
    AutonomousCooldownState,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousScheduleProfile,
    MissionControlCycle,
    MissionControlSession,
    MissionControlState,
)


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


class SessionTimingPolicyTests(TestCase):
    def test_profile_endpoint_bootstraps_defaults(self):
        response = self.client.get(reverse('mission_control:schedule-profiles'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(profile['slug'] == 'balanced_local' for profile in payload))

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
