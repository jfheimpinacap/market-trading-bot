from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.broker_bridge.models import BrokerDryRunResponse, BrokerIntentStatus
from apps.broker_bridge.services import create_intent, run_dry_run, validate_intent
from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, OperatingEnvelope
from apps.execution_simulator.services import create_order
from apps.incident_commander.models import IncidentRecord, IncidentSeverity, IncidentStatus
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.operator_queue.models import OperatorQueueItem
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.runtime_governor.models import RuntimeStateStatus
from apps.runtime_governor.services import get_runtime_state
from apps.safety_guard.services.kill_switch import get_or_create_config


class BrokerBridgeServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.order = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('2.0000'))

    def _create_certification(self, *, level: str = CertificationLevel.PAPER_CERTIFIED_BALANCED, auto_execution_allowed: bool = True):
        envelope = OperatingEnvelope.objects.create(auto_execution_allowed=auto_execution_allowed)
        snapshot = CertificationEvidenceSnapshot.objects.create()
        CertificationRun.objects.create(
            recommendation_code=CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            certification_level=level,
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )

    def test_create_intent_from_paper_order(self):
        intent = create_intent(source_type='paper_order', source_id=self.order.id)
        self.assertEqual(intent.source_type, 'paper_order')
        self.assertEqual(intent.status, BrokerIntentStatus.DRAFT)
        self.assertEqual(intent.market_id, self.market.id)

    def test_validation_blocked_by_runtime_safety_and_incident(self):
        self._create_certification(level=CertificationLevel.NOT_CERTIFIED, auto_execution_allowed=False)
        runtime = get_runtime_state()
        runtime.status = RuntimeStateStatus.PAUSED
        runtime.save(update_fields=['status', 'updated_at'])
        safety = get_or_create_config()
        safety.kill_switch_enabled = True
        safety.save(update_fields=['kill_switch_enabled', 'updated_at'])
        IncidentRecord.objects.create(
            incident_type='execution_anomaly',
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            title='Critical incident',
            summary='block',
            source_app='tests',
            first_seen_at=self.order.created_at,
            last_seen_at=self.order.created_at,
        )

        intent = create_intent(source_type='paper_order', source_id=self.order.id)
        validation = validate_intent(intent=intent)
        self.assertFalse(validation.is_valid)
        self.assertEqual(intent.status, BrokerIntentStatus.REJECTED)
        self.assertGreaterEqual(len(validation.blocking_reasons), 1)

    def test_validation_success_and_dry_run_accept(self):
        self._create_certification(level=CertificationLevel.PAPER_CERTIFIED_BALANCED, auto_execution_allowed=True)
        intent = create_intent(source_type='paper_order', source_id=self.order.id)
        validation = validate_intent(intent=intent)
        self.assertTrue(validation.is_valid)
        self.assertEqual(intent.status, BrokerIntentStatus.DRY_RUN_READY)

        dry_run = run_dry_run(intent=intent)
        self.assertEqual(dry_run.simulated_response, BrokerDryRunResponse.ACCEPTED)

    def test_manual_review_creates_operator_queue_item(self):
        self._create_certification(level=CertificationLevel.PAPER_CERTIFIED_BALANCED, auto_execution_allowed=False)
        intent = create_intent(source_type='manual', source_id='x', payload={'quantity': '1.0000', 'side': 'BUY', 'order_type': 'market', 'market_id': self.market.id})
        validation = validate_intent(intent=intent)
        self.assertTrue(validation.is_valid)
        self.assertTrue(validation.requires_manual_review)
        self.assertTrue(OperatorQueueItem.objects.filter(metadata__broker_bridge_intent_id=intent.id).exists())


class BrokerBridgeApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.order = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('1.0000'))
        envelope = OperatingEnvelope.objects.create(auto_execution_allowed=True)
        snapshot = CertificationEvidenceSnapshot.objects.create()
        CertificationRun.objects.create(
            recommendation_code=CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            certification_level=CertificationLevel.PAPER_CERTIFIED_BALANCED,
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )

    def test_endpoints(self):
        create_res = self.client.post(reverse('broker_bridge:create-intent'), {'source_type': 'paper_order', 'source_id': str(self.order.id)}, format='json')
        self.assertEqual(create_res.status_code, 201)
        intent_id = create_res.json()['intent']['id']

        validate_res = self.client.post(reverse('broker_bridge:validate-intent', kwargs={'pk': intent_id}), {}, format='json')
        dry_run_res = self.client.post(reverse('broker_bridge:dry-run-intent', kwargs={'pk': intent_id}), {}, format='json')
        list_res = self.client.get(reverse('broker_bridge:intents'))
        detail_res = self.client.get(reverse('broker_bridge:intent-detail', kwargs={'pk': intent_id}))
        summary_res = self.client.get(reverse('broker_bridge:summary'))

        self.assertEqual(validate_res.status_code, 200)
        self.assertEqual(dry_run_res.status_code, 200)
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(summary_res.status_code, 200)
