from django.core.management.base import BaseCommand

from apps.signals.services import generate_demo_signals


class Command(BaseCommand):
    help = 'Generate or refresh demo market signals using explicit local heuristics and mock agents.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Limit the number of markets evaluated.')
        parser.add_argument('--market-id', type=int, default=None, help='Generate signals only for one market id.')
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Delete existing signals before regeneration.',
        )

    def handle(self, *args, **options):
        self.stdout.write('Generating demo signals using local heuristics...')
        result = generate_demo_signals(
            limit=options['limit'],
            market_id=options['market_id'],
            clear_existing=options['clear_existing'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                'Demo signals generation complete. '
                f'run_id={result.run.id} markets_evaluated={result.markets_evaluated} '
                f'signals_created={result.signals_created} signals_updated={result.signals_updated}'
            )
        )
