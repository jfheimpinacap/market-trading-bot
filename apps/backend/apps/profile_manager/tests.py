import json

from django.test import TestCase
from django.urls import reverse

from apps.profile_manager.models import ProfileDecisionMode, RegimeClassification
from apps.profile_manager.services.decision import build_profile_decision
from apps.profile_manager.services.regime import classify_regime
from apps.profile_manager.services import run_profile_governance
from apps.runtime_governor.models import RuntimeModeState


class ProfileManagerTests(TestCase):
    def test_regime_classification_basics(self):
        regime, reasons, constraints = classify_regime({
            'safety_kill_switch': False,
            'safety_hard_stop': False,
            'readiness_status': 'READY',
            'runtime_mode': 'PAPER_AUTO',
            'throttle_state': 'NORMAL',
            'drawdown_pct': 0.01,
            'market_concentration': 0.20,
            'provider_concentration': 0.20,
            'queue_pressure': 0,
        })
        self.assertEqual(regime, RegimeClassification.NORMAL)
        self.assertIn('stable', reasons)
        self.assertEqual(constraints, [])

    def test_conservative_decision_for_drawdown_and_concentration(self):
        payload = build_profile_decision(
            regime=RegimeClassification.DRAWDOWN_MODE,
            state={'runtime_mode': 'PAPER_AUTO', 'readiness_status': 'READY', 'safety_status': 'HEALTHY', 'throttle_state': 'THROTTLED'},
            reason_codes=['drawdown_high'],
            constraints=[],
        )
        self.assertEqual(payload['target_signal_profile'], 'conservative_signal')
        self.assertEqual(payload['decision_mode'], ProfileDecisionMode.APPLY_SAFE)

    def test_runtime_readiness_blocking_forces_conservative_constraints(self):
        payload = build_profile_decision(
            regime=RegimeClassification.NORMAL,
            state={'runtime_mode': 'OBSERVE_ONLY', 'readiness_status': 'NOT_READY', 'safety_status': 'HEALTHY', 'throttle_state': 'NORMAL'},
            requested_mode=ProfileDecisionMode.APPLY_SAFE,
        )
        self.assertEqual(payload['target_mission_control_profile'], 'conservative_mission_control')
        self.assertIn('READINESS_BLOCK', payload['blocking_constraints'])

    def test_recommendation_vs_apply_safe(self):
        run_recommend = run_profile_governance(decision_mode=ProfileDecisionMode.RECOMMEND_ONLY)
        self.assertFalse(run_recommend.decision.is_applied)

        run_apply = run_profile_governance(decision_mode=ProfileDecisionMode.APPLY_SAFE)
        self.assertTrue(run_apply.decision.is_applied)

    def test_endpoints(self):
        RuntimeModeState.objects.all().delete()
        client = self.client
        run_response = client.post(reverse('profile_manager:run-governance'), data=json.dumps({}), content_type='application/json')
        self.assertEqual(run_response.status_code, 200)
        run_id = run_response.json()['id']
        decision_id = run_response.json()['decision']['id']

        self.assertEqual(client.get(reverse('profile_manager:run-list')).status_code, 200)
        self.assertEqual(client.get(reverse('profile_manager:run-detail', kwargs={'pk': run_id})).status_code, 200)
        self.assertEqual(client.get(reverse('profile_manager:current')).status_code, 200)
        self.assertEqual(client.get(reverse('profile_manager:summary')).status_code, 200)
        self.assertEqual(client.post(reverse('profile_manager:apply-decision', kwargs={'decision_id': decision_id}), data='{}', content_type='application/json').status_code, 200)
