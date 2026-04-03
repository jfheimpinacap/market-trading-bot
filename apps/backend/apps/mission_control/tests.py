from unittest.mock import patch
import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from django.utils import timezone

from apps.mission_control.models import (
    AutonomousProfileSwitchRecord,
    AutonomousCooldownState,
    AutonomousSessionInterventionDecision,
    AutonomousResumeDecision,
    AutonomousResumeRecord,
    AutonomousSessionRecoveryRecommendation,
    AutonomousSessionRecoverySnapshot,
    AutonomousRuntimeSession,
    AutonomousRuntimeTick,
    AutonomousScheduleProfile,
    MissionControlCycle,
    MissionControlSession,
    MissionControlState,
    GovernanceReviewItem,
)
from apps.mission_control.services.collect import collect_governance_review_candidates
from apps.mission_control.services.prioritize import assign_severity_and_priority
from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureCoordinationRun,
    PortfolioExposureDecision,
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
