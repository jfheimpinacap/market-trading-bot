from apps.connector_lab.models import AdapterQualificationCaseStatus, AdapterReadinessCode, AdapterReadinessRecommendation


def build_readiness_recommendation(*, run, results, missing_capabilities: list[str], unsupported_paths: list[str]) -> AdapterReadinessRecommendation:
    reason_codes: list[str] = []
    failed = [result for result in results if result.result_status == AdapterQualificationCaseStatus.FAILED]
    unsupported = [result for result in results if result.result_status == AdapterQualificationCaseStatus.UNSUPPORTED]

    if failed:
        reason_codes.append('QUALIFICATION_FAILED_CASES')
    if unsupported:
        reason_codes.append('UNSUPPORTED_PATHS_PRESENT')
    if missing_capabilities:
        reason_codes.append('MISSING_CAPABILITIES')
    if any(result.case_group == 'reconciliation' and result.result_status != AdapterQualificationCaseStatus.PASSED for result in results):
        reason_codes.append('RECONCILIATION_GAPS')

    if failed:
        recommendation = AdapterReadinessCode.NOT_READY
        rationale = 'Qualification has failed checks that block read-only preparation.'
    elif any(code == 'RECONCILIATION_GAPS' for code in reason_codes):
        recommendation = AdapterReadinessCode.RECONCILIATION_GAPS
        rationale = 'Adapter passes core contract checks but reconciliation parity still has technical gaps.'
    elif missing_capabilities:
        recommendation = AdapterReadinessCode.INCOMPLETE_MAPPING
        rationale = 'Adapter contract is mostly stable but required capabilities are incomplete.'
    elif unsupported_paths:
        recommendation = AdapterReadinessCode.MANUAL_REVIEW_REQUIRED
        rationale = 'Adapter is sandbox qualified with unsupported paths requiring manual review.'
    elif any(result.result_status == AdapterQualificationCaseStatus.WARNING for result in results):
        recommendation = AdapterReadinessCode.READ_ONLY_PREPARED
        rationale = 'Adapter is technically ready for a controlled future read-only phase with warnings.'
    else:
        recommendation = AdapterReadinessCode.SANDBOX_CERTIFIED
        rationale = 'Adapter is sandbox certified against payload/response/account/reconciliation qualification checks.'

    return AdapterReadinessRecommendation.objects.create(
        qualification_run=run,
        recommendation=recommendation,
        rationale=rationale,
        reason_codes=reason_codes,
        missing_capabilities=missing_capabilities,
        unsupported_paths=unsupported_paths,
        metadata={'failed_cases': [result.case_code for result in failed], 'unsupported_cases': [result.case_code for result in unsupported]},
    )
