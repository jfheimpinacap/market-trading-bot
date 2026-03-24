from django.core.management.base import BaseCommand

from apps.learning_memory.services import (
    ingest_recent_evaluation_runs,
    ingest_recent_reviews,
    ingest_recent_safety_events,
    rebuild_active_adjustments,
)


class Command(BaseCommand):
    help = 'Rebuild heuristic learning memory and active conservative adjustments from reviews/evaluation/safety signals.'

    def handle(self, *args, **options):
        self.stdout.write('Rebuilding learning memory entries from local demo sources...')
        reviews = ingest_recent_reviews()
        evaluation = ingest_recent_evaluation_runs()
        safety = ingest_recent_safety_events()
        adjusted = rebuild_active_adjustments()
        self.stdout.write(
            self.style.SUCCESS(
                f'Learning memory rebuilt. created_reviews={reviews}, created_evaluation={evaluation}, '
                f'created_safety={safety}, adjustments_processed={adjusted["adjustments_processed"]}'
            )
        )
