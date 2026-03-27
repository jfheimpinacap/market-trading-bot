from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.broker_bridge.services import create_intent, run_dry_run, validate_intent
from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, OperatingEnvelope
from apps.execution_simulator.services import create_order
from apps.execution_venue.models import VenueParityStatus, VenueResponseStatus
from apps.execution_venue.services.adapters import NullSandboxVenueAdapter
from apps.execution_venue.services.parity import run_parity
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.portfolio import ensure_demo_account


class ExecutionVenueServiceTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        self.order = create_order(market=self.market, side='BUY_YES', requested_quantity=Decimal('2.0000'))
        envelope = OperatingEnvelope.objects.create(auto_execution_allowed=True)
        snapshot = CertificationEvidenceSnapshot.objects.create()
        CertificationRun.objects.create(
            recommendation_code=CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            certification_level=CertificationLevel.PAPER_CERTIFIED_BALANCED,
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )
        self.intent = create_intent(source_type='paper_order', source_id=self.order.id)
        validate_intent(intent=self.intent)
        run_dry_run(intent=self.intent)
        self.adapter = NullSandboxVenueAdapter()

    def test_build_payload_from_broker_intent(self):
        payload = self.adapter.build_payload(self.intent)
        self.assertEqual(payload.source_intent_id, self.intent.id)
        self.assertEqual(payload.venue_name, 'sandbox_venue')
        self.assertEqual(payload.order_type, 'market_like')

    def test_validate_payload_with_capability_constraints(self):
        payload = self.adapter.build_payload(self.intent)
        payload.external_market_id = ''
        payload.save(update_fields=['external_market_id', 'updated_at'])
        valid, reason_codes, _, missing_fields = self.adapter.validate_payload(payload)
        self.assertFalse(valid)
        self.assertIn('MISSING_EXTERNAL_MARKET_ID', reason_codes)
        self.assertIn('external_market_id', missing_fields)

    def test_sandbox_dry_run_response(self):
        payload = self.adapter.build_payload(self.intent)
        response = self.adapter.dry_run(payload)
        self.assertEqual(response.normalized_status, VenueResponseStatus.ACCEPTED)

    def test_unsupported_action_handling(self):
        capability = self.adapter.get_capabilities()
        capability.supports_close_order = False
        capability.save(update_fields=['supports_close_order', 'updated_at'])

        self.intent.side = 'CLOSE'
        self.intent.order_type = 'close_order'
        self.intent.save(update_fields=['side', 'order_type', 'updated_at'])

        payload = self.adapter.build_payload(self.intent)
        response = self.adapter.dry_run(payload)
        self.assertEqual(response.normalized_status, VenueResponseStatus.UNSUPPORTED)

    def test_basic_parity_run(self):
        parity_run = run_parity(self.intent)
        self.assertIn(parity_run.parity_status, {VenueParityStatus.PARITY_OK, VenueParityStatus.PARITY_GAP})
        self.assertIsNotNone(parity_run.payload)
        self.assertIsNotNone(parity_run.response)


class ExecutionVenueApiTests(TestCase):
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
        self.intent = create_intent(source_type='paper_order', source_id=self.order.id)

    def test_execution_venue_endpoints(self):
        capabilities = self.client.get(reverse('execution_venue:capabilities'))
        build_payload = self.client.post(reverse('execution_venue:build-payload', kwargs={'intent_id': self.intent.id}), {}, format='json')
        dry_run = self.client.post(reverse('execution_venue:dry-run', kwargs={'intent_id': self.intent.id}), {}, format='json')
        parity = self.client.post(reverse('execution_venue:run-parity', kwargs={'intent_id': self.intent.id}), {}, format='json')
        parity_runs = self.client.get(reverse('execution_venue:parity-runs'))
        summary = self.client.get(reverse('execution_venue:summary'))

        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(build_payload.status_code, 201)
        self.assertEqual(dry_run.status_code, 201)
        self.assertEqual(parity.status_code, 201)
        self.assertEqual(parity_runs.status_code, 200)
        self.assertEqual(summary.status_code, 200)
