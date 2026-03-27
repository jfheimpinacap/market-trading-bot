from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.broker_bridge.services import create_intent, run_dry_run, validate_intent
from apps.certification_board.models import CertificationEvidenceSnapshot, CertificationLevel, CertificationRecommendationCode, CertificationRun, OperatingEnvelope
from apps.execution_simulator.services import create_order
from apps.execution_venue.services.adapters import NullSandboxVenueAdapter
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.portfolio import ensure_demo_account, get_active_account
from apps.venue_account.models import VenueIssueType, VenueReconciliationStatus
from apps.venue_account.services import rebuild_sandbox_mirror, run_reconciliation


class VenueAccountServiceTests(TestCase):
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

        adapter = NullSandboxVenueAdapter()
        payload = adapter.build_payload(self.intent)
        adapter.dry_run(payload)

    def test_rebuild_sandbox_mirror_creates_snapshots(self):
        result = rebuild_sandbox_mirror()
        self.assertGreaterEqual(result['orders_updated'], 1)
        self.assertGreaterEqual(result['positions_updated'], 0)
        self.assertIsNotNone(result['account_snapshot_id'])

    def test_reconciliation_run_records_mismatch_when_external_order_missing(self):
        # force mismatch: internal filled quantity diverges from external mirror derived fill quantity
        self.order.remaining_quantity = Decimal('1.0000')
        self.order.save(update_fields=['remaining_quantity', 'updated_at'])
        run = run_reconciliation({'triggered_from': 'test'})
        self.assertEqual(run.status, VenueReconciliationStatus.PARITY_GAP)
        self.assertTrue(run.issues.filter(issue_type=VenueIssueType.FILL_QUANTITY_MISMATCH).exists())


class VenueAccountApiTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        ensure_demo_account()
        self.client = APIClient()
        market = Market.objects.get(slug='will-candidate-a-win-the-2028-election')
        order = create_order(market=market, side='BUY_YES', requested_quantity=Decimal('1.0000'))
        envelope = OperatingEnvelope.objects.create(auto_execution_allowed=True)
        snapshot = CertificationEvidenceSnapshot.objects.create()
        CertificationRun.objects.create(
            recommendation_code=CertificationRecommendationCode.HOLD_CURRENT_CERTIFICATION,
            certification_level=CertificationLevel.PAPER_CERTIFIED_BALANCED,
            evidence_snapshot=snapshot,
            operating_envelope=envelope,
        )
        intent = create_intent(source_type='paper_order', source_id=order.id)
        validate_intent(intent=intent)
        run_dry_run(intent=intent)
        adapter = NullSandboxVenueAdapter()
        payload = adapter.build_payload(intent)
        adapter.dry_run(payload)

    def test_venue_account_endpoints(self):
        current = self.client.get(reverse('venue_account:current'))
        orders = self.client.get(reverse('venue_account:orders'))
        positions = self.client.get(reverse('venue_account:positions'))
        balances = self.client.get(reverse('venue_account:balances'))
        run = self.client.post(reverse('venue_account:run-reconciliation'), {}, format='json')
        runs = self.client.get(reverse('venue_account:reconciliation-runs'))
        summary = self.client.get(reverse('venue_account:summary'))

        self.assertEqual(current.status_code, 200)
        self.assertEqual(orders.status_code, 200)
        self.assertEqual(positions.status_code, 200)
        self.assertEqual(balances.status_code, 200)
        self.assertEqual(run.status_code, 201)
        self.assertEqual(runs.status_code, 200)
        self.assertEqual(summary.status_code, 200)

        run_id = run.data['id']
        run_detail = self.client.get(reverse('venue_account:reconciliation-run-detail', kwargs={'pk': run_id}))
        self.assertEqual(run_detail.status_code, 200)
        self.assertIn('issues', run_detail.data)
