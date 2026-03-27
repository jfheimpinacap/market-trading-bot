from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.broker_bridge.services import create_intent, run_dry_run, validate_intent
from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, OperatingEnvelope
from apps.chaos_lab.models import ChaosExperiment, ChaosExperimentType, ChaosRun, ChaosRunStatus, ResilienceBenchmark
from apps.execution_simulator.services import create_order
from apps.go_live_gate.models import GoLiveApprovalStatus
from apps.go_live_gate.services import create_approval_request, run_checklist, run_rehearsal
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.runtime_governor.models import RuntimeMode, RuntimeStateStatus
from apps.runtime_governor.services import get_runtime_state, set_runtime_mode
from apps.safety_guard.services.kill_switch import get_or_create_config


class GoLiveGateServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.order = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('1.0000'))
        envelope = OperatingEnvelope.objects.create(max_autonomy_mode_allowed=RuntimeMode.PAPER_SEMI_AUTO, auto_execution_allowed=True)
        snapshot = CertificationEvidenceSnapshot.objects.create()
        CertificationRun.objects.create(
            recommendation_code=CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            certification_level=CertificationLevel.PAPER_CERTIFIED_BALANCED,
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )
        runtime_state = get_runtime_state()
        runtime_state.current_mode = RuntimeMode.PAPER_SEMI_AUTO
        runtime_state.status = RuntimeStateStatus.ACTIVE
        runtime_state.save(update_fields=['current_mode', 'status', 'updated_at'])
        safety = get_or_create_config()
        safety.kill_switch_enabled = False
        safety.status = 'HEALTHY'
        safety.save(update_fields=['kill_switch_enabled', 'status', 'updated_at'])

        experiment = ChaosExperiment.objects.create(name='queue pressure', slug='queue-pressure-test', experiment_type=ChaosExperimentType.QUEUE_PRESSURE_SPIKE, target_module='operator_queue')
        chaos_run = ChaosRun.objects.create(experiment=experiment, status=ChaosRunStatus.SUCCESS, started_at=self.order.created_at)
        ResilienceBenchmark.objects.create(run=chaos_run, experiment=experiment, resilience_score='82.00', recovery_success_rate='1.0')

        self.intent = create_intent(source_type='paper_order', source_id=self.order.id)
        validate_intent(intent=self.intent)
        run_dry_run(intent=self.intent)

    def test_firewall_and_checklist(self):
        checklist = run_checklist(manual_inputs={'operator_review_complete': True})
        self.assertTrue(checklist.passed)
        self.assertIn('dry_run_success_rate', checklist.passed_items)

    def test_checklist_blocked_by_cert_runtime_safety_incidents(self):
        IncidentRecord.objects.create(
            incident_type='execution_anomaly',
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            title='critical open incident',
            summary='block rehearsal',
            source_app='tests',
            first_seen_at=self.order.created_at,
            last_seen_at=self.order.created_at,
        )
        runtime = get_runtime_state()
        runtime.current_mode = RuntimeMode.PAPER_ASSIST
        runtime.status = RuntimeStateStatus.PAUSED
        runtime.save(update_fields=['status', 'updated_at'])
        safety = get_or_create_config()
        safety.kill_switch_enabled = True
        safety.save(update_fields=['kill_switch_enabled', 'updated_at'])

        checklist = run_checklist(manual_inputs={'operator_review_complete': False})
        self.assertFalse(checklist.passed)
        self.assertGreaterEqual(len(checklist.failed_items), 1)

    def test_approval_and_rehearsal(self):
        checklist = run_checklist(manual_inputs={'operator_review_complete': True})
        approval = create_approval_request(
            requested_by='operator-1',
            rationale='manual review completed',
            scope='global',
            requested_mode='PRELIVE_REHEARSAL',
            checklist_run=checklist,
        )
        approval.status = GoLiveApprovalStatus.APPROVED
        approval.save(update_fields=['status', 'updated_at'])

        run = run_rehearsal(intent=self.intent, requested_by='operator-1')
        self.assertTrue(run.allowed_to_proceed_in_rehearsal)
        self.assertTrue(run.blocked_by_firewall)

    def test_rehearsal_without_approval_creates_operator_queue_item(self):
        run_checklist(manual_inputs={'operator_review_complete': True})
        run = run_rehearsal(intent=self.intent, requested_by='operator-1')
        self.assertFalse(run.allowed_to_proceed_in_rehearsal)
        self.assertTrue(OperatorQueueItem.objects.filter(metadata__go_live_rehearsal_run_id=run.id).exists())


class GoLiveGateApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_endpoints(self):
        state_res = self.client.get(reverse('go_live_gate:state'))
        checklist_res = self.client.post(reverse('go_live_gate:run-checklist'), {'manual_inputs': {'operator_review_complete': False}}, format='json')
        approvals_res = self.client.get(reverse('go_live_gate:approvals'))
        summary_res = self.client.get(reverse('go_live_gate:summary'))

        self.assertEqual(state_res.status_code, 200)
        self.assertEqual(checklist_res.status_code, 201)
        self.assertEqual(approvals_res.status_code, 200)
        self.assertEqual(summary_res.status_code, 200)
