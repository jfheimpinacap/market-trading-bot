from django.core.management.base import BaseCommand, CommandError

from apps.prediction_training.models import PredictionDatasetRun
from apps.prediction_training.services.training import run_training


class Command(BaseCommand):
    help = 'Train calibrated XGBoost prediction model from a dataset run.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset-run-id', type=int)
        parser.add_argument('--model-name', default='xgboost_baseline')

    def handle(self, *args, **options):
        dataset_run_id = options.get('dataset_run_id')
        dataset_run = None
        if dataset_run_id:
            dataset_run = PredictionDatasetRun.objects.filter(id=dataset_run_id).first()
        if dataset_run is None:
            dataset_run = PredictionDatasetRun.objects.order_by('-created_at', '-id').first()
        if dataset_run is None:
            raise CommandError('No dataset run available. Build dataset first.')
        result = run_training(dataset_run=dataset_run, model_name=options['model_name'])
        self.stdout.write(self.style.SUCCESS(f'Training run id={result.training_run.id}, artifact id={result.model_artifact.id if result.model_artifact else "n/a"}'))
