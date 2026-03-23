from django.core.management.base import BaseCommand

from apps.signals.seeds import seed_mock_agents


class Command(BaseCommand):
    help = 'Create or refresh the local demo mock agents used by the signals layer.'

    def handle(self, *args, **options):
        self.stdout.write('Ensuring demo mock agents exist...')
        counts = seed_mock_agents()
        self.stdout.write(
            self.style.SUCCESS(
                'Mock agents ready. '
                f"total={counts['total']} created={counts['created']} updated={counts['updated']}"
            )
        )
