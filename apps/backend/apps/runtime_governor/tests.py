from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile, ReadinessStatus
from apps.runtime_governor.models import RuntimeMode, RuntimeSetBy, RuntimeTransitionLog
from apps.runtime_governor.services import get_capabilities_for_current_mode, get_runtime_state, set_runtime_mode
from apps.safety_guard.services.kill_switch import enable_kill_switch


class RuntimeGovernorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.profile = ReadinessProfile.objects.create(name='Balanced', slug='balanced', profile_type='balanced')

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
