from __future__ import annotations

from collections import Counter

from apps.autonomy_launch.models import LaunchRun
from apps.autonomy_launch.services.authorization import upsert_authorization_from_snapshot
from apps.autonomy_launch.services.candidates import list_launch_candidates
from apps.autonomy_launch.services.preflight import evaluate_preflight
from apps.autonomy_launch.services.readiness import create_readiness_snapshot
from apps.autonomy_launch.services.recommendation import create_recommendations
from apps.autonomy_program.services.state import recompute_program_state
from apps.autonomy_scheduler.services.windows import get_active_window


def run_preflight(*, actor: str = 'operator-ui'):
    candidates = list_launch_candidates()
    program_state = recompute_program_state()
    active_window = get_active_window()

    run = LaunchRun.objects.create(
        candidate_count=len(candidates),
        program_posture=program_state.concurrency_posture,
        active_window=active_window,
        metadata={'actor': actor},
    )

    snapshots = []
    for admission in candidates:
        preflight_result = evaluate_preflight(admission=admission, program_state=program_state, active_window=active_window)
        snapshot = create_readiness_snapshot(preflight_result=preflight_result, launch_run=run)
        upsert_authorization_from_snapshot(snapshot=snapshot, actor=actor)
        snapshots.append(snapshot)

    status_counter = Counter(snapshot.readiness_status for snapshot in snapshots)
    recommendation_summary = Counter()
    recommendations = create_recommendations(launch_run=run, snapshots=snapshots)
    for recommendation in recommendations:
        recommendation_summary[recommendation.recommendation_type] += 1

    run.ready_count = status_counter.get('READY_TO_START', 0)
    run.waiting_count = status_counter.get('WAITING', 0)
    run.blocked_count = status_counter.get('BLOCKED', 0)
    run.approval_required_count = sum(1 for snapshot in snapshots if snapshot.unresolved_approvals_count > 0)
    run.recommendation_summary = dict(recommendation_summary)
    run.metadata = {**(run.metadata or {}), 'snapshot_count': len(snapshots)}
    run.save(update_fields=['ready_count', 'waiting_count', 'blocked_count', 'approval_required_count', 'recommendation_summary', 'metadata', 'updated_at'])

    return {'run': run, 'snapshots': snapshots, 'recommendations': recommendations, 'candidates': candidates}
