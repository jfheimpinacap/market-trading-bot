from django.core.management.base import BaseCommand, CommandError

from apps.postmortem_demo.services import generate_trade_reviews


class Command(BaseCommand):
    help = 'Generate demo post-mortem trade reviews for executed paper trades.'

    def add_arguments(self, parser):
        parser.add_argument('--trade-id', type=int, help='Generate or refresh a review for one paper trade ID.')
        parser.add_argument('--limit', type=int, help='Only process the most recent N executed paper trades.')
        parser.add_argument(
            '--refresh-existing',
            action='store_true',
            help='Refresh reviews that already exist instead of leaving them untouched.',
        )

    def handle(self, *args, **options):
        trade_id = options.get('trade_id')
        limit = options.get('limit')
        refresh_existing = options.get('refresh_existing', False)

        if limit is not None and limit <= 0:
            raise CommandError('--limit must be greater than zero.')

        self.stdout.write('Generating demo trade reviews using local post-mortem heuristics...')
        results = generate_trade_reviews(trade_id=trade_id, limit=limit, refresh_existing=refresh_existing)

        if trade_id and not results:
            raise CommandError(f'Paper trade {trade_id} was not found or is not executable for review.')

        created = sum(1 for result in results if result.created)
        refreshed = sum(1 for result in results if not result.created and refresh_existing)
        stale_marked = sum(1 for result in results if result.stale_marked)
        skipped = len(results) - created - refreshed

        for result in results:
            action = 'created' if result.created else 'refreshed' if refresh_existing else 'skipped'
            if result.stale_marked and not refresh_existing:
                action = 'marked-stale'
            review = result.review
            self.stdout.write(
                f' - trade={review.paper_trade_id} review={review.id} outcome={review.outcome} status={review.review_status} action={action}'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Trade review generation complete. processed={len(results)} created={created} refreshed={refreshed} stale_marked={stale_marked} skipped={skipped}'
            )
        )
