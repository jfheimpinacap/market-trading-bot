from django.core.management.base import BaseCommand

from apps.paper_trading.models import PaperAccount
from apps.paper_trading.services.portfolio import get_active_account
from apps.paper_trading.services.valuation import revalue_account


class Command(BaseCommand):
    help = 'Revalue the active demo paper portfolio and persist a snapshot.'

    def add_arguments(self, parser):
        parser.add_argument('--account-id', type=int, help='Optional paper account id to revalue.')

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        if account_id:
            account = PaperAccount.objects.get(pk=account_id)
        else:
            account = get_active_account()

        revalue_account(account, create_snapshot=True)
        self.stdout.write(
            self.style.SUCCESS(
                f'Paper portfolio refreshed: account={account.slug} cash={account.cash_balance} equity={account.equity}',
            )
        )
