from django.core.management.base import BaseCommand, CommandError

from apps.real_data_sync.services import run_provider_sync


class Command(BaseCommand):
    help = 'Run hardened read-only provider sync for real market snapshots.'

    def add_arguments(self, parser):
        parser.add_argument('--provider', required=True, choices=['kalshi', 'polymarket'])
        parser.add_argument('--sync-type', default='full', choices=['full', 'incremental', 'single_market', 'active_only'])
        parser.add_argument('--active-only', action='store_true')
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--market-id')
        parser.add_argument('--triggered-from', default='management_command')

    def handle(self, *args, **options):
        provider = options['provider']
        limit = int(options['limit'])
        if limit < 1:
            raise CommandError('--limit must be >= 1')

        run = run_provider_sync(
            provider=provider,
            sync_type=options.get('sync_type'),
            active_only=bool(options.get('active_only')),
            limit=limit,
            market_id=options.get('market_id'),
            triggered_from=options.get('triggered_from') or 'management_command',
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Real sync completed run_id={run.id} provider={run.provider} status={run.status} '
                f'seen={run.markets_seen} updated={run.markets_updated} snapshots={run.snapshots_created} errors={run.errors_count}'
            )
        )
