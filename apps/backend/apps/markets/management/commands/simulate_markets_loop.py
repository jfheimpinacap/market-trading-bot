from __future__ import annotations

import time
from random import Random

from django.core.management.base import BaseCommand

from apps.markets.simulation import MarketSimulationEngine


class Command(BaseCommand):
    help = 'Run demo market simulation ticks in a simple local loop.'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=float, default=10.0, help='Seconds to wait between ticks.')
        parser.add_argument('--iterations', type=int, default=None, help='Number of ticks to run. Omit for continuous mode.')
        parser.add_argument('--limit', type=int, default=None, help='Maximum number of markets to process per tick.')
        parser.add_argument('--dry-run', action='store_true', help='Compute ticks without persisting changes.')
        parser.add_argument('--seed', type=int, default=None, help='Optional random seed for reproducible runs.')

    def handle(self, *args, **options):
        interval = max(0.0, options['interval'])
        iterations = options['iterations']
        rng = Random(options['seed']) if options['seed'] is not None else None
        engine = MarketSimulationEngine(rng=rng)

        tick_number = 0
        self.stdout.write(self.style.MIGRATE_HEADING('Starting demo market simulation loop. Press Ctrl+C to stop.'))

        try:
            while iterations is None or tick_number < iterations:
                tick_number += 1
                result = engine.run_tick(dry_run=options['dry_run'], limit=options['limit'])
                self.stdout.write(
                    f'Tick {tick_number}: processed={result.processed}, updated={result.updated}, '
                    f'skipped={result.skipped}, snapshots={result.snapshots_created}'
                )
                if iterations is None or tick_number < iterations:
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Simulation loop interrupted by user.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Simulation loop finished after {tick_number} tick(s).'))
