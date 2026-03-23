from django.core.management.base import BaseCommand

from apps.paper_trading.services.portfolio import ensure_demo_account


class Command(BaseCommand):
    help = 'Create or ensure the default demo paper trading account exists.'

    def handle(self, *args, **options):
        self.stdout.write('Ensuring demo paper trading account exists...')
        account, created = ensure_demo_account()
        action = 'created' if created else 'already existed'
        self.stdout.write(
            self.style.SUCCESS(
                f'Demo paper account {action}: slug={account.slug} cash_balance={account.cash_balance} equity={account.equity}',
            )
        )
