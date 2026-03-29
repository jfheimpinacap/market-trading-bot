from apps.autonomy_launch.models import LaunchReadinessSnapshot, LaunchReadinessStatus


def _derive_status(result: dict) -> str:
    if any(code in result['reason_codes'] for code in ['PROGRAM_FROZEN', 'DOMAIN_CONFLICT', 'INCIDENT_IMPACT', 'ROLLOUT_PRESSURE']):
        return LaunchReadinessStatus.BLOCKED
    if any(code in result['reason_codes'] for code in ['WINDOW_NOT_OPEN', 'DEPENDENCY_BLOCKED']):
        return LaunchReadinessStatus.WAITING
    if result['requires_approval'] or result['unresolved_checkpoints_count'] > 0:
        return LaunchReadinessStatus.CAUTION
    return LaunchReadinessStatus.READY_TO_START


def _score(result: dict, status: str) -> int:
    score = 100
    score -= min(result['unresolved_checkpoints_count'] * 15, 45)
    score -= min(result['unresolved_approvals_count'] * 20, 40)
    score -= min(len(result['blockers']) * 10, 50)
    if status == LaunchReadinessStatus.BLOCKED:
        score -= 40
    elif status == LaunchReadinessStatus.WAITING:
        score -= 20
    elif status == LaunchReadinessStatus.CAUTION:
        score -= 10
    return max(score, 0)


def create_readiness_snapshot(*, preflight_result: dict, launch_run=None) -> LaunchReadinessSnapshot:
    status = _derive_status(preflight_result)
    return LaunchReadinessSnapshot.objects.create(
        campaign=preflight_result['campaign'],
        launch_run=launch_run,
        admission_status=preflight_result['admission'].status,
        program_posture=preflight_result['program_posture'],
        active_window_status=preflight_result['active_window_status'],
        unresolved_checkpoints_count=preflight_result['unresolved_checkpoints_count'],
        unresolved_approvals_count=preflight_result['unresolved_approvals_count'],
        dependency_blocked=preflight_result['dependency_blocked'],
        domain_conflict=preflight_result['domain_conflict'],
        incident_impact=preflight_result['incident_impact'],
        degraded_impact=preflight_result['degraded_impact'],
        rollout_observation_impact=preflight_result['rollout_observation_impact'],
        readiness_score=_score(preflight_result, status),
        readiness_status=status,
        blockers=preflight_result['blockers'],
        metadata={'reason_codes': preflight_result['reason_codes'], 'impacted_domains': preflight_result['impacted_domains']},
    )
