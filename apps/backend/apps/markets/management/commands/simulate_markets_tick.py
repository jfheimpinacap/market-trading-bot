from __future__ import annotations

from random import Random

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.markets.simulation import MarketSimulationEngine


class Command(BaseCommand):
    help = 'Run one local simulation tick over eligible demo markets and create fresh snapshots.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Maximum number of markets to process.')
        parser.add_argument('--dry-run', action='store_true', help='Show simulated changes without persisting them.')
        parser.add_argument('--seed', type=int, default=None, help='Optional random seed for reproducible development runs.')

    def handle(self, *args, **options):
        now = timezone.now()
        rng = Random(options['seed']) if options['seed'] is not None else None
        engine = MarketSimulationEngine(rng=rng)
        result = engine.run_tick(now=now, dry_run=options['dry_run'], limit=options['limit'])

        mode = 'DRY RUN' if options['dry_run'] else 'LIVE RUN'
        self.stdout.write(self.style.MIGRATE_HEADING(f'Simulating demo markets tick ({mode}) at {now.isoformat()}'))
        self.stdout.write(f'Markets processed: {result.processed}')
        self.stdout.write(f'Markets updated: {result.updated}')
        self.stdout.write(f'Markets skipped: {result.skipped}')
        self.stdout.write(f'Snapshots created: {result.snapshots_created}')

        if result.state_changes:
            self.stdout.write('State changes:')
            for change in result.state_changes:
                self.stdout.write(f' - {change}')
        else:
            self.stdout.write('State changes: none')

        skipped_results = [item for item in result.market_results if item.skipped_reason]
        if skipped_results:
            self.stdout.write('Skipped markets:')
            for item in skipped_results:
                self.stdout.write(f' - {item.title} ({item.skipped_reason})')

        updated_results = [item for item in result.market_results if item.updated]
        if updated_results:
            self.stdout.write('Updated markets:')
            for item in updated_results:
                self.stdout.write(
                    f' - {item.title}: probability {item.probability_before} -> {item.probability_after} '
                    f'[{item.previous_status} -> {item.next_status}]'
                )

        self.stdout.write(self.style.SUCCESS('Simulation tick complete.'))
