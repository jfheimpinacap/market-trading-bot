from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.markets.demo_data import seed_demo_markets


class Command(BaseCommand):
    help = 'Populate the local database with coherent demo markets, events, snapshots, and rules.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding demo markets data...'))
        try:
            counts = seed_demo_markets(stdout=self.stdout)
        except DatabaseError as exc:
            raise CommandError(f'Unable to seed demo markets data: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Demo markets data ready.'))
        self.stdout.write(
            'Created or updated: '
            f"providers={counts['providers']}, "
            f"events={counts['events']}, "
            f"markets={counts['markets']}, "
            f"snapshots={counts['snapshots']}, "
            f"rules={counts['rules']}"
        )
