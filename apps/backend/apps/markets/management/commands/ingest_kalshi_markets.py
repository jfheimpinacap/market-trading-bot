from django.core.management.base import BaseCommand

from apps.markets.services.real_data_ingestion import ingest_provider_markets


class Command(BaseCommand):
    help = 'Ingest Kalshi real market data in read-only mode.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50)
        parser.add_argument('--active-only', action='store_true')
        parser.add_argument('--provider-market-id', type=str)
        parser.add_argument('--query', type=str)

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting Kalshi read-only ingestion...'))
        result = ingest_provider_markets(
            'kalshi',
            limit=options['limit'],
            active_only=options['active_only'],
            provider_market_id=options.get('provider_market_id'),
            query=options.get('query'),
        )
        self.stdout.write(self.style.SUCCESS(
            'Kalshi ingestion complete. '
            f"fetched={result.fetched} "
            f"events_created={result.events_created} events_updated={result.events_updated} "
            f"markets_created={result.markets_created} markets_updated={result.markets_updated} "
            f"snapshots_created={result.snapshots_created}"
        ))
