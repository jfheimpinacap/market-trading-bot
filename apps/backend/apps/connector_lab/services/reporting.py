from apps.connector_lab.models import AdapterQualificationRun, AdapterReadinessRecommendation


def build_summary() -> dict:
    latest_run = AdapterQualificationRun.objects.select_related('fixture_profile').order_by('-created_at', '-id').first()
    latest_readiness = AdapterReadinessRecommendation.objects.select_related('qualification_run').order_by('-created_at', '-id').first()

    runs = AdapterQualificationRun.objects.all()
    return {
        'sandbox_only': True,
        'total_runs': runs.count(),
        'success_runs': runs.filter(qualification_status='SUCCESS').count(),
        'partial_runs': runs.filter(qualification_status='PARTIAL').count(),
        'failed_runs': runs.filter(qualification_status='FAILED').count(),
        'latest_run': {
            'id': latest_run.id,
            'adapter_name': latest_run.adapter_name,
            'qualification_status': latest_run.qualification_status,
            'summary': latest_run.summary,
            'fixture_profile': latest_run.fixture_profile.slug if latest_run.fixture_profile else None,
            'created_at': latest_run.created_at,
        } if latest_run else None,
        'current_readiness': {
            'id': latest_readiness.id,
            'run_id': latest_readiness.qualification_run_id,
            'recommendation': latest_readiness.recommendation,
            'rationale': latest_readiness.rationale,
            'reason_codes': latest_readiness.reason_codes,
            'missing_capabilities': latest_readiness.missing_capabilities,
            'unsupported_paths': latest_readiness.unsupported_paths,
            'created_at': latest_readiness.created_at,
        } if latest_readiness else None,
    }
