from __future__ import annotations

from typing import Any

from apps.runtime_governor.models import RuntimeTuningContextSnapshot
from apps.runtime_governor.services.tuning_diff import build_tuning_context_diffs


def build_latest_diff_links(*, latest_snapshots: list[RuntimeTuningContextSnapshot]) -> dict[str, dict[str, Any]]:
    diff_rows_by_snapshot_id = {
        row['current_snapshot_id']: row for row in build_tuning_context_diffs(snapshots=latest_snapshots)
    }
    links_by_scope: dict[str, dict[str, Any]] = {}
    for snapshot in latest_snapshots:
        diff_row = diff_rows_by_snapshot_id.get(snapshot.id, {})
        previous_snapshot_id = diff_row.get('previous_snapshot_id')
        if previous_snapshot_id is None:
            links_by_scope[snapshot.source_scope] = {
                'latest_diff_snapshot_id': None,
                'latest_diff_status': None,
                'latest_diff_summary': None,
            }
            continue
        links_by_scope[snapshot.source_scope] = {
            'latest_diff_snapshot_id': diff_row.get('current_snapshot_id'),
            'latest_diff_status': diff_row.get('drift_status'),
            'latest_diff_summary': diff_row.get('diff_summary'),
        }
    return links_by_scope
