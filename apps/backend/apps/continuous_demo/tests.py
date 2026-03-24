from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.continuous_demo.models import ContinuousDemoSession, SessionStatus
from apps.continuous_demo.services.loop import start_session, stop_session
from apps.learning_memory.models import LearningRebuildRun
from apps.markets.demo_data import seed_demo_markets
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.semi_auto_demo.models import PendingApproval, PendingApprovalStatus
from apps.signals.seeds import seed_mock_agents
from apps.signals.services import generate_demo_signals


class ContinuousDemoServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        seed_mock_agents()
        generate_demo_signals()
        ensure_demo_account()

    def tearDown(self):
        stop_session(kill_switch=True)

    def test_start_session_rejects_second_running_session(self):
        session = start_session(settings_overrides={'cycle_interval_seconds': 2})
        self.assertIsNotNone(session.id)

        with self.assertRaisesMessage(ValueError, 'already running'):
            start_session(settings_overrides={'cycle_interval_seconds': 2})

    def test_run_single_cycle_endpoint_creates_cycle(self):
        client = APIClient()
        response = client.post(reverse('continuous_demo:run-cycle'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload['cycle_number'], 1)
        self.assertIn(payload['status'], ['SUCCESS', 'PARTIAL', 'FAILED'])

    def test_pause_resume_stop_endpoints(self):
        client = APIClient()
        start_response = client.post(reverse('continuous_demo:start'), {'cycle_interval_seconds': 2}, format='json')
        self.assertEqual(start_response.status_code, 200)

        pause_response = client.post(reverse('continuous_demo:pause'), {}, format='json')
        self.assertEqual(pause_response.status_code, 200)
        self.assertEqual(pause_response.json()['session_status'], SessionStatus.PAUSED)

        resume_response = client.post(reverse('continuous_demo:resume'), {}, format='json')
        self.assertEqual(resume_response.status_code, 200)
        self.assertEqual(resume_response.json()['session_status'], SessionStatus.RUNNING)

        stop_response = client.post(reverse('continuous_demo:stop'), {'kill_switch': True}, format='json')
        self.assertEqual(stop_response.status_code, 200)

    def test_loop_respects_pending_approvals(self):
        client = APIClient()
        response = client.post(reverse('continuous_demo:run-cycle'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        pending_count = PendingApproval.objects.filter(status=PendingApprovalStatus.PENDING).count()
        payload = response.json()
        self.assertEqual(payload['approval_required_count'], pending_count)

    def test_main_status_and_history_endpoints(self):
        client = APIClient()
        client.post(reverse('continuous_demo:run-cycle'), {}, format='json')

        self.assertEqual(client.get(reverse('continuous_demo:status')).status_code, 200)
        self.assertEqual(client.get(reverse('continuous_demo:session-list')).status_code, 200)
        self.assertEqual(client.get(reverse('continuous_demo:cycle-list')).status_code, 200)

        session = ContinuousDemoSession.objects.order_by('-id').first()
        self.assertIsNotNone(session)
        self.assertEqual(client.get(reverse('continuous_demo:session-detail', kwargs={'pk': session.id})).status_code, 200)

    def test_learning_rebuild_not_triggered_when_disabled(self):
        client = APIClient()
        before = LearningRebuildRun.objects.count()
        response = client.post(reverse('continuous_demo:run-cycle'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('learning_rebuild', payload['details'])
        self.assertFalse(payload['details']['learning_rebuild'].get('triggered', True))
        self.assertEqual(LearningRebuildRun.objects.count(), before)

    def test_learning_rebuild_can_trigger_on_cycle_cadence(self):
        client = APIClient()
        settings = {
            'cycle_interval_seconds': 2,
            'learning_rebuild_enabled': True,
            'learning_rebuild_every_n_cycles': 1,
        }
        start_response = client.post(reverse('continuous_demo:start'), settings, format='json')
        self.assertEqual(start_response.status_code, 200)
        before = LearningRebuildRun.objects.count()
        manual_cycle = client.post(reverse('continuous_demo:run-cycle'), {}, format='json')
        self.assertEqual(manual_cycle.status_code, 200)
        self.assertIn('learning_rebuild', manual_cycle.json()['details'])
        self.assertGreaterEqual(LearningRebuildRun.objects.count(), before)
