from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.opportunity_supervisor.services.execution_path import resolve_execution_path
from apps.markets.models import Market
from apps.paper_trading.models import PaperPosition, PaperPositionStatus
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.portfolio_governor.models import PortfolioThrottleState
from apps.portfolio_governor.models import (
    PortfolioExposureClusterSnapshot,
    PortfolioExposureConcentrationStatus,
    PortfolioExposureConflictReview,
    PortfolioExposureCoordinationRun,
)
from apps.portfolio_governor.services import run_exposure_coordination_review, run_portfolio_governance
from apps.portfolio_governor.services.conflict_review import review_cluster_conflicts
from apps.portfolio_governor.services.decision import derive_exposure_decision
from apps.portfolio_governor.services.throttle import build_throttle_decision_payload


class PortfolioGovernorTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.account, _ = ensure_demo_account()
        self.market = Market.objects.first()

    def _create_position(self, market_value: Decimal):
        PaperPosition.objects.create(
            account=self.account,
            market=self.market,
            side='YES',
            quantity=Decimal('10'),
            average_entry_price=Decimal('0.60'),
            current_mark_price=Decimal('0.61'),
            cost_basis=market_value,
            market_value=market_value,
            status=PaperPositionStatus.OPEN,
        )

    def test_exposure_snapshot_basics(self):
        self._create_position(Decimal('1200'))
        run = run_portfolio_governance()
        self.assertIsNotNone(run.exposure_snapshot)
        self.assertEqual(run.exposure_snapshot.open_positions, 1)
        self.assertGreaterEqual(run.exposure_snapshot.total_exposure, Decimal('1200'))

    def test_throttle_states(self):
        base = {
            'open_positions': 2,
            'recent_drawdown_pct': 0.01,
            'concentration_market_ratio': 0.2,
            'concentration_provider_ratio': 0.2,
            'cash_reserve_ratio': 0.4,
        }
        profile = {
            'default_max_new_positions': 3,
            'drawdown_caution_pct': 0.06,
            'drawdown_throttle_pct': 0.10,
            'drawdown_block_pct': 0.14,
            'cash_reserve_caution_ratio': 0.20,
            'cash_reserve_throttle_ratio': 0.12,
            'cash_reserve_block_ratio': 0.08,
            'max_market_concentration_ratio': 0.45,
            'max_provider_concentration_ratio': 0.55,
            'max_open_positions': 8,
            'queue_pressure_throttle': 8,
            'close_reduce_events_throttle': 5,
        }
        normal = build_throttle_decision_payload(snapshot=base, profile=profile, regime_signals=['normal'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        caution = build_throttle_decision_payload(snapshot={**base, 'recent_drawdown_pct': 0.07}, profile=profile, regime_signals=['drawdown_caution'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        throttled = build_throttle_decision_payload(snapshot={**base, 'concentration_market_ratio': 0.5}, profile=profile, regime_signals=['concentrated'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})
        blocked = build_throttle_decision_payload(snapshot={**base, 'recent_drawdown_pct': 0.2}, profile=profile, regime_signals=['drawdown_caution'], queue_pressure=0, close_reduce_events=0, runtime_mode='PAPER_AUTO', safety_status={'status': 'HEALTHY'})

        self.assertEqual(normal['state'], PortfolioThrottleState.NORMAL)
        self.assertEqual(caution['state'], PortfolioThrottleState.CAUTION)
        self.assertEqual(throttled['state'], PortfolioThrottleState.THROTTLED)
        self.assertEqual(blocked['state'], PortfolioThrottleState.BLOCK_NEW_ENTRIES)

    def test_opportunity_path_blocked_by_portfolio_throttle(self):
        decision = resolve_execution_path(
            policy_decision='AUTO_APPROVE',
            runtime_mode='PAPER_AUTO',
            safety_status='HEALTHY',
            blocked_reasons=[],
            risk_level='LOW',
            has_allocation=True,
            portfolio_throttle_state='BLOCK_NEW_ENTRIES',
            portfolio_size_multiplier='0',
        )
        self.assertEqual(decision.path, 'BLOCKED')

    def test_api_endpoints(self):
        client = APIClient()
        run_response = client.post(reverse('portfolio_governor:run-governance'), {}, format='json')
        self.assertEqual(run_response.status_code, 200)
        run_id = run_response.json()['id']

        self.assertEqual(client.get(reverse('portfolio_governor:run-list')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:run-detail', kwargs={'pk': run_id})).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:throttle')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:summary')).status_code, 200)

    def test_exposure_coordination_endpoints(self):
        client = APIClient()
        run_response = client.post(reverse('portfolio_governor:run-exposure-coordination-review'), {}, format='json')
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-coordination-runs')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-cluster-snapshots')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:session-exposure-contributions')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-conflict-reviews')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-decisions')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-recommendations')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-coordination-summary')).status_code, 200)
        self.assertEqual(client.post(reverse('portfolio_governor:run-exposure-apply-review'), {}, format='json').status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-runs')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-targets')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-decisions')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-records')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-recommendations')).status_code, 200)
        self.assertEqual(client.get(reverse('portfolio_governor:exposure-apply-summary')).status_code, 200)


class ExposureCoordinationDecisionTests(TestCase):
    def setUp(self):
        self.run = PortfolioExposureCoordinationRun.objects.create()
        self.cluster = PortfolioExposureClusterSnapshot.objects.create(
            linked_run=self.run,
            cluster_label='test-cluster',
            cluster_type='MIXED',
            net_direction='LONG_BIAS',
            session_count=4,
            open_position_count=2,
            pending_dispatch_count=2,
            aggregate_notional_pressure=Decimal('3000'),
            aggregate_risk_pressure_state='THROTTLED',
            concentration_status=PortfolioExposureConcentrationStatus.HIGH,
            cluster_summary='Synthetic test cluster',
        )

    def test_high_concentration_generates_throttle(self):
        reviews = review_cluster_conflicts(cluster=self.cluster)
        concentration = next(r for r in reviews if r.review_type == 'CONCENTRATION_RISK')
        decision = derive_exposure_decision(review=concentration)
        self.assertEqual(decision.decision_type, 'THROTTLE_NEW_ENTRIES')

    def test_pending_dispatch_overload_generates_defer(self):
        review = PortfolioExposureConflictReview.objects.create(
            linked_cluster_snapshot=self.cluster,
            review_type='PENDING_DISPATCH_OVERLOAD',
            review_severity='HIGH',
            review_summary='dispatch overload',
        )
        decision = derive_exposure_decision(review=review)
        self.assertEqual(decision.decision_type, 'DEFER_PENDING_DISPATCH')

    def test_redundant_low_value_can_park(self):
        review = PortfolioExposureConflictReview.objects.create(
            linked_cluster_snapshot=self.cluster,
            review_type='LOW_VALUE_CAPACITY_WASTE',
            review_severity='CAUTION',
            review_summary='low value stack',
        )
        decision = derive_exposure_decision(review=review)
        self.assertEqual(decision.decision_type, 'PARK_WEAKER_SESSION')

    def test_directional_conflict_requires_manual_review(self):
        review = PortfolioExposureConflictReview.objects.create(
            linked_cluster_snapshot=self.cluster,
            review_type='DIRECTIONAL_CONFLICT',
            review_severity='HIGH',
            review_summary='direction conflict',
        )
        decision = derive_exposure_decision(review=review)
        self.assertEqual(decision.decision_type, 'REQUIRE_MANUAL_EXPOSURE_REVIEW')
        self.assertFalse(decision.auto_applicable)

    def test_healthy_cluster_keeps_exposure(self):
        review = PortfolioExposureConflictReview.objects.create(
            linked_cluster_snapshot=self.cluster,
            review_type='REDUNDANT_SESSION_STACKING',
            review_severity='INFO',
            review_summary='healthy',
        )
        decision = derive_exposure_decision(review=review)
        self.assertEqual(decision.decision_type, 'KEEP_EXPOSURE_AS_IS')

    def test_summary_endpoint_fields(self):
        run_exposure_coordination_review()
        client = APIClient()
        response = client.get(reverse('portfolio_governor:exposure-coordination-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('clusters_reviewed', payload)
        self.assertIn('throttles', payload)

from apps.autonomous_trader.models import (
    AutonomousDispatchRecord,
    AutonomousExecutionDecision,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionIntakeRun,
)
from apps.mission_control.models import AutonomousRuntimeSession, AutonomousRuntimeSessionStatus
from apps.portfolio_governor.models import (
    PortfolioExposureApplyDecision,
    PortfolioExposureApplyRecord,
    PortfolioExposureApplyTarget,
    PortfolioExposureDecision,
    PortfolioExposureDecisionStatus,
    PortfolioExposureDecisionType,
    SessionExposureContribution,
)
from apps.portfolio_governor.services.run import apply_exposure_decision, run_exposure_apply_review


class ExposureApplyBridgeTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.market = Market.objects.first()
        self.run = PortfolioExposureCoordinationRun.objects.create()
        self.cluster = PortfolioExposureClusterSnapshot.objects.create(
            linked_run=self.run,
            cluster_label='apply-bridge-cluster',
            cluster_type='MIXED',
            net_direction='LONG_BIAS',
            session_count=2,
            open_position_count=1,
            pending_dispatch_count=1,
            aggregate_notional_pressure=Decimal('2200'),
            aggregate_risk_pressure_state='THROTTLED',
            concentration_status=PortfolioExposureConcentrationStatus.HIGH,
            cluster_summary='Apply bridge cluster',
        )

    def _build_dispatch_for_session(self, session: AutonomousRuntimeSession) -> AutonomousDispatchRecord:
        intake_run = AutonomousExecutionIntakeRun.objects.create()
        intake_candidate = AutonomousExecutionIntakeCandidate.objects.create(intake_run=intake_run, linked_market=self.market, intake_status='READY_FOR_AUTONOMOUS_EXECUTION')
        execution_decision = AutonomousExecutionDecision.objects.create(linked_intake_candidate=intake_candidate, decision_type='EXECUTE_NOW')
        dispatch = AutonomousDispatchRecord.objects.create(linked_execution_decision=execution_decision, dispatch_status='QUEUED')
        SessionExposureContribution.objects.create(
            linked_session=session,
            linked_cluster_snapshot=self.cluster,
            linked_dispatch_record=dispatch,
            contribution_role='REDUNDANT',
            contribution_strength='LOW',
            contribution_summary='redundant dispatch',
        )
        return dispatch

    def test_throttle_apply_sets_cluster_gate(self):
        session = AutonomousRuntimeSession.objects.create(runtime_mode='PAPER_AUTO')
        SessionExposureContribution.objects.create(
            linked_session=session,
            linked_cluster_snapshot=self.cluster,
            contribution_role='SUPPORTING',
            contribution_strength='MEDIUM',
        )
        decision = PortfolioExposureDecision.objects.create(
            linked_cluster_snapshot=self.cluster,
            decision_type=PortfolioExposureDecisionType.THROTTLE_NEW_ENTRIES,
            decision_status=PortfolioExposureDecisionStatus.PROPOSED,
            auto_applicable=True,
            decision_summary='Throttle cluster',
        )
        apply_run = apply_exposure_decision(decision=decision)
        self.cluster.refresh_from_db()
        self.assertTrue(self.cluster.metadata.get('exposure_new_entries_throttled'))
        self.assertEqual(apply_run.applied_count, 1)

    def test_pending_dispatch_is_deferred(self):
        session = AutonomousRuntimeSession.objects.create(runtime_mode='PAPER_AUTO')
        dispatch = self._build_dispatch_for_session(session)
        decision = PortfolioExposureDecision.objects.create(
            linked_cluster_snapshot=self.cluster,
            decision_type=PortfolioExposureDecisionType.DEFER_PENDING_DISPATCH,
            decision_status=PortfolioExposureDecisionStatus.PROPOSED,
            auto_applicable=True,
            decision_summary='Defer pending dispatch',
        )
        apply_exposure_decision(decision=decision)
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.dispatch_status, 'SKIPPED')
        self.assertTrue(dispatch.metadata.get('deferred_by_exposure_apply'))

    def test_redundant_session_can_be_parked(self):
        session = AutonomousRuntimeSession.objects.create(runtime_mode='PAPER_AUTO')
        SessionExposureContribution.objects.create(
            linked_session=session,
            linked_cluster_snapshot=self.cluster,
            contribution_role='LOW_VALUE',
            contribution_strength='LOW',
        )
        decision = PortfolioExposureDecision.objects.create(
            linked_cluster_snapshot=self.cluster,
            decision_type=PortfolioExposureDecisionType.PARK_WEAKER_SESSION,
            decision_status=PortfolioExposureDecisionStatus.PROPOSED,
            auto_applicable=True,
            decision_summary='Park weaker session',
        )
        apply_exposure_decision(decision=decision)
        session.refresh_from_db()
        self.assertEqual(session.session_status, AutonomousRuntimeSessionStatus.PAUSED)

    def test_ambiguous_cluster_stays_manual_review(self):
        decision = PortfolioExposureDecision.objects.create(
            linked_cluster_snapshot=self.cluster,
            decision_type=PortfolioExposureDecisionType.REQUIRE_MANUAL_EXPOSURE_REVIEW,
            decision_status=PortfolioExposureDecisionStatus.PROPOSED,
            auto_applicable=False,
            decision_summary='Manual review only',
        )
        run = apply_exposure_decision(decision=decision)
        apply_decision = PortfolioExposureApplyDecision.objects.filter(linked_apply_run=run).first()
        record = PortfolioExposureApplyRecord.objects.filter(linked_apply_decision=apply_decision).first()
        self.assertEqual(apply_decision.apply_status, 'SKIPPED')
        self.assertEqual(record.effect_type, 'MANUAL_REVIEW_ONLY')

    def test_exposure_apply_summary_endpoint(self):
        run_exposure_apply_review()
        client = APIClient()
        response = client.get(reverse('portfolio_governor:exposure-apply-summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('decisions_considered', payload)
        self.assertIn('deferred_dispatches', payload)
