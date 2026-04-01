from unittest.mock import patch
import json

from django.test import TestCase
from django.urls import reverse

from apps.mission_control.models import MissionControlCycle, MissionControlSession, MissionControlState


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
