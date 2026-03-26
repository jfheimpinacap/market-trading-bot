from django.core.management.base import BaseCommand, CommandError

from apps.prediction_training.services.dataset import build_prediction_dataset


class Command(BaseCommand):
    help = 'Build historical dataset for prediction model training.'

    def add_arguments(self, parser):
        parser.add_argument('--name', default='manual_dataset')
        parser.add_argument('--horizon-hours', type=int, default=24)

    def handle(self, *args, **options):
        horizon = options['horizon_hours']
        if horizon < 1:
            raise CommandError('horizon-hours must be >= 1')
        result = build_prediction_dataset(name=options['name'], horizon_hours=horizon)
        self.stdout.write(self.style.SUCCESS(f'Dataset run created: id={result.dataset_run.id} rows={result.dataset_run.rows_built}'))
