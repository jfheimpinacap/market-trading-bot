from decimal import Decimal

from apps.broker_bridge.models import BrokerOrderIntent
from apps.broker_bridge.services import create_intent
from apps.connector_lab.models import (
    AdapterQualificationCaseStatus,
    AdapterQualificationResult,
    AdapterQualificationRun,
    AdapterQualificationStatus,
)
from apps.connector_lab.services.cases import list_cases
from apps.connector_lab.services.recommendation import build_readiness_recommendation
from apps.execution_simulator.services import create_order
from apps.execution_venue.models import VenueResponseStatus
from apps.execution_venue.services import NullSandboxVenueAdapter
from apps.go_live_gate.models import GoLiveChecklistRun
from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market
from apps.paper_trading.services.portfolio import ensure_demo_account
from apps.venue_account.models import VenueOrderSnapshot, VenueReconciliationStatus
from apps.venue_account.services.reconciliation import run_reconciliation
from apps.venue_account.services.snapshots import build_account_snapshot, build_order_snapshots


def _ensure_intent() -> BrokerOrderIntent:
    existing = BrokerOrderIntent.objects.order_by('-created_at', '-id').first()
    if existing:
        return existing

    seed_demo_markets()
    ensure_demo_account()
    market = Market.objects.order_by('id').first()
    if not market:
        raise ValueError('No market available to build qualification intent.')
    order = create_order(market=market, side='BUY_YES', requested_quantity=Decimal('1.0000'))
    return create_intent(source_type='paper_order', source_id=order.id)


def _save_result(run: AdapterQualificationRun, case: dict, status: str, issues: list[str] | None = None, warnings: list[str] | None = None, details: dict | None = None):
    return AdapterQualificationResult.objects.create(
        qualification_run=run,
        case_code=case['code'],
        case_group=case['group'],
        result_status=status,
        issues=issues or [],
        warnings=warnings or [],
        details=details or {},
    )


def execute_qualification_suite(*, fixture_profile, metadata: dict | None = None) -> AdapterQualificationRun:
    metadata = metadata or {}
    adapter = NullSandboxVenueAdapter()
    capability = adapter.get_capabilities()
    fixture_data = fixture_profile.metadata or {}
    run = AdapterQualificationRun.objects.create(
        adapter_name=adapter.name,
        adapter_type='sandbox_null',
        fixture_profile=fixture_profile,
        qualification_status=AdapterQualificationStatus.RUNNING,
        details={'metadata': metadata, 'fixture_profile': fixture_profile.slug},
    )

    base_intent = _ensure_intent()
    cases = list_cases()
    results: list[AdapterQualificationResult] = []

    unsupported_capability = fixture_data.get('unsupported_capability')
    original_capability_value = None
    if unsupported_capability and hasattr(capability, unsupported_capability):
        original_capability_value = getattr(capability, unsupported_capability)
        setattr(capability, unsupported_capability, False)
        capability.save(update_fields=[unsupported_capability, 'updated_at'])

    for case in cases:
        code = case['code']
        if code == 'basic_buy_yes_mapping':
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            valid, reason_codes, warnings, _ = adapter.validate_payload(payload)
            status = AdapterQualificationCaseStatus.PASSED if valid and payload.order_type == 'market_like' else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, issues=reason_codes, warnings=warnings, details={'payload_id': payload.id}))

        elif code == 'limit_like_mapping':
            base_intent.order_type = 'limit'
            base_intent.limit_price = Decimal('0.6200')
            base_intent.save(update_fields=['order_type', 'limit_price', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            valid, reason_codes, warnings, _ = adapter.validate_payload(payload)
            passed = valid and payload.order_type == 'limit_like' and payload.limit_price is not None
            results.append(_save_result(run, case, AdapterQualificationCaseStatus.PASSED if passed else AdapterQualificationCaseStatus.FAILED, issues=reason_codes, warnings=warnings))

        elif code == 'unsupported_order_type':
            base_intent.order_type = 'iceberg'
            base_intent.save(update_fields=['order_type', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            valid, reason_codes, _, _ = adapter.validate_payload(payload)
            response = adapter.dry_run(payload, metadata={'qualification_case': code})
            supported = valid and response.normalized_status not in {VenueResponseStatus.UNSUPPORTED, VenueResponseStatus.INVALID_PAYLOAD}
            status = AdapterQualificationCaseStatus.UNSUPPORTED if not supported else AdapterQualificationCaseStatus.WARNING
            results.append(_save_result(run, case, status, issues=reason_codes or [response.normalized_status], details={'response_id': response.id}))

        elif code == 'reduce_only_mapping':
            base_intent.side = 'REDUCE'
            base_intent.order_type = 'market'
            base_intent.save(update_fields=['side', 'order_type', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            status = AdapterQualificationCaseStatus.PASSED if payload.reduce_only else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, details={'reduce_only': payload.reduce_only}))

        elif code == 'close_order_mapping':
            base_intent.side = 'CLOSE'
            base_intent.order_type = 'close_order'
            base_intent.save(update_fields=['side', 'order_type', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            status = AdapterQualificationCaseStatus.PASSED if payload.close_flag else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, details={'close_flag': payload.close_flag}))

        elif code == 'response_normalization_accept':
            base_intent.side = 'BUY'
            base_intent.order_type = 'market'
            base_intent.quantity = Decimal(str(fixture_data.get('quantity', '1.0000')))
            base_intent.save(update_fields=['side', 'order_type', 'quantity', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code, 'force_manual_confirmation': fixture_data.get('force_manual_confirmation', False)})
            response = adapter.dry_run(payload, metadata={'qualification_case': code})
            valid_statuses = {VenueResponseStatus.ACCEPTED, VenueResponseStatus.HOLD, VenueResponseStatus.REQUIRES_CONFIRMATION}
            status = AdapterQualificationCaseStatus.PASSED if response.normalized_status in valid_statuses else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, details={'response_status': response.normalized_status}))

        elif code == 'response_normalization_reject':
            base_intent.order_type = 'limit'
            base_intent.limit_price = None
            if fixture_data.get('force_missing_market'):
                base_intent.symbol = ''
                base_intent.market_ref = ''
            base_intent.save(update_fields=['order_type', 'limit_price', 'symbol', 'market_ref', 'updated_at'])
            payload = adapter.build_payload(base_intent, metadata={'qualification_case': code})
            response = adapter.dry_run(payload, metadata={'qualification_case': code})
            expected = {VenueResponseStatus.INVALID_PAYLOAD, VenueResponseStatus.UNSUPPORTED, VenueResponseStatus.REJECTED}
            status = AdapterQualificationCaseStatus.PASSED if response.normalized_status in expected else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, issues=response.reason_codes, details={'response_status': response.normalized_status}))

        elif code == 'account_snapshot_build':
            snapshot = build_account_snapshot()
            status = AdapterQualificationCaseStatus.PASSED if snapshot.id else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, details={'snapshot_id': snapshot.id}))

        elif code == 'order_snapshot_update':
            updated = build_order_snapshots()
            status = AdapterQualificationCaseStatus.PASSED if updated > 0 or VenueOrderSnapshot.objects.exists() else AdapterQualificationCaseStatus.WARNING
            results.append(_save_result(run, case, status, warnings=['No order snapshots updated in this run.'] if updated == 0 else [], details={'updated': updated}))

        elif code == 'reconciliation_parity_ok':
            reconciliation = run_reconciliation(metadata={'qualification_case': code})
            status = AdapterQualificationCaseStatus.PASSED if reconciliation.status in {VenueReconciliationStatus.PARITY_OK, VenueReconciliationStatus.PARITY_GAP} else AdapterQualificationCaseStatus.FAILED
            results.append(_save_result(run, case, status, details={'reconciliation_status': reconciliation.status}))

        elif code == 'reconciliation_mismatch_detection':
            warnings: list[str] = []
            if fixture_data.get('inject_reconciliation_drift'):
                warnings.append('drift_fixture_enabled')
            reconciliation = run_reconciliation(metadata={'qualification_case': code, 'inject_drift': bool(fixture_data.get('inject_reconciliation_drift'))})
            mismatch_detected = reconciliation.mismatches_count > 0 or bool(reconciliation.issues.exists())
            status = AdapterQualificationCaseStatus.PASSED if mismatch_detected else AdapterQualificationCaseStatus.WARNING
            results.append(_save_result(run, case, status, warnings=warnings, details={'mismatches_count': reconciliation.mismatches_count}))

    missing_capabilities = []
    if not capability.supports_market_like:
        missing_capabilities.append('supports_market_like')
    if not capability.supports_limit_like:
        missing_capabilities.append('supports_limit_like')
    if not capability.supports_reduce_only:
        missing_capabilities.append('supports_reduce_only')
    if not capability.supports_close_order:
        missing_capabilities.append('supports_close_order')


    if unsupported_capability and original_capability_value is not None:
        setattr(capability, unsupported_capability, original_capability_value)
        capability.save(update_fields=[unsupported_capability, 'updated_at'])

    unsupported_paths = [result.case_code for result in results if result.result_status == AdapterQualificationCaseStatus.UNSUPPORTED]
    recommendation = build_readiness_recommendation(
        run=run,
        results=results,
        missing_capabilities=missing_capabilities,
        unsupported_paths=unsupported_paths,
    )

    failed_count = len([r for r in results if r.result_status == AdapterQualificationCaseStatus.FAILED])
    unsupported_count = len(unsupported_paths)
    run.qualification_status = AdapterQualificationStatus.SUCCESS if failed_count == 0 and unsupported_count == 0 else (AdapterQualificationStatus.PARTIAL if failed_count == 0 else AdapterQualificationStatus.FAILED)
    run.capability_checks_run = len([case for case in cases if case['group'] == 'capabilities'])
    run.payload_checks_run = len([case for case in cases if case['group'] == 'payload'])
    run.response_checks_run = len([case for case in cases if case['group'] == 'response'])
    run.account_mirror_checks_run = len([case for case in cases if case['group'] == 'account_mirror'])
    run.reconciliation_checks_run = len([case for case in cases if case['group'] == 'reconciliation'])
    run.summary = (
        f'Completed {len(results)} checks. status={run.qualification_status}. '
        f'recommendation={recommendation.recommendation}. failed={failed_count}. unsupported={unsupported_count}.'
    )
    run.details = {
        **(run.details or {}),
        'result_counts': {
            'passed': len([r for r in results if r.result_status == AdapterQualificationCaseStatus.PASSED]),
            'warning': len([r for r in results if r.result_status == AdapterQualificationCaseStatus.WARNING]),
            'unsupported': unsupported_count,
            'failed': failed_count,
        },
        'go_live_checklists': GoLiveChecklistRun.objects.count(),
    }
    run.save(
        update_fields=[
            'qualification_status',
            'capability_checks_run',
            'payload_checks_run',
            'response_checks_run',
            'account_mirror_checks_run',
            'reconciliation_checks_run',
            'summary',
            'details',
            'updated_at',
        ]
    )
    return run
