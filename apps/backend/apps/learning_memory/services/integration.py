from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.learning_memory.models import LearningRebuildRun
from apps.learning_memory.services.adjustments import rebuild_active_adjustments
from apps.learning_memory.services.ingest import ingest_recent_evaluation_runs, ingest_recent_reviews, ingest_recent_safety_events


DEFAULT_MAX_ADJUSTMENT_MAGNITUDE = Decimal('0.2000')


def run_learning_rebuild(
    *,
    triggered_from: str = LearningRebuildRun.TriggeredFrom.MANUAL,
    related_session_id: int | None = None,
    related_cycle_id: int | None = None,
    max_adjustment_magnitude: Decimal = DEFAULT_MAX_ADJUSTMENT_MAGNITUDE,
) -> LearningRebuildRun:
    started_at = timezone.now()
    rebuild_run = LearningRebuildRun.objects.create(
        status=LearningRebuildRun.Status.SUCCESS,
        triggered_from=triggered_from,
        related_session_id=related_session_id,
        related_cycle_id=related_cycle_id,
        started_at=started_at,
        details={},
    )

    try:
        created_reviews = ingest_recent_reviews()
        created_eval = ingest_recent_evaluation_runs()
        created_safety = ingest_recent_safety_events()
        adjusted = rebuild_active_adjustments(max_adjustment_magnitude=max_adjustment_magnitude)

        warnings: list[str] = []
        if adjusted['memory_entries_processed'] == 0:
            warnings.append('No learning memory entries available; adjustments were rebuilt from an empty window.')

        rebuild_run.status = LearningRebuildRun.Status.PARTIAL if warnings else LearningRebuildRun.Status.SUCCESS
        rebuild_run.memory_entries_processed = adjusted['memory_entries_processed']
        rebuild_run.adjustments_created = adjusted['adjustments_created']
        rebuild_run.adjustments_updated = adjusted['adjustments_updated']
        rebuild_run.adjustments_deactivated = adjusted['adjustments_deactivated']
        rebuild_run.summary = (
            f"Rebuild completed: entries={rebuild_run.memory_entries_processed}, created={rebuild_run.adjustments_created}, "
            f"updated={rebuild_run.adjustments_updated}, deactivated={rebuild_run.adjustments_deactivated}."
        )
        rebuild_run.details = {
            'created_memory_entries': created_reviews + created_eval + created_safety,
            'created_from_reviews': created_reviews,
            'created_from_evaluation': created_eval,
            'created_from_safety': created_safety,
            'max_adjustment_magnitude': str(max_adjustment_magnitude),
            'warnings': warnings,
        }
    except Exception as exc:
        rebuild_run.status = LearningRebuildRun.Status.FAILED
        rebuild_run.summary = f'Learning rebuild failed: {exc}'
        rebuild_run.details = {'error': str(exc)}

    rebuild_run.finished_at = timezone.now()
    rebuild_run.save(
        update_fields=[
            'status',
            'finished_at',
            'memory_entries_processed',
            'adjustments_created',
            'adjustments_updated',
            'adjustments_deactivated',
            'summary',
            'details',
            'updated_at',
        ]
    )
    return rebuild_run


def should_rebuild_learning(*, settings: dict, cycle_number: int, reviews_generated: bool) -> tuple[bool, str]:
    if not settings.get('learning_rebuild_enabled', False):
        return False, 'Automatic rebuild is disabled for safety.'

    if settings.get('learning_rebuild_after_reviews', False) and reviews_generated:
        return True, 'Triggered after review generation.'

    every_n = int(settings.get('learning_rebuild_every_n_cycles', 0) or 0)
    if every_n > 0 and cycle_number % every_n == 0:
        return True, f'Triggered on cycle cadence (every {every_n} cycles).'

    return False, 'No rebuild trigger matched this cycle.'
