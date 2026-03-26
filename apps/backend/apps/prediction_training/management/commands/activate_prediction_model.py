from django.core.management.base import BaseCommand, CommandError

from apps.prediction_training.models import PredictionModelArtifact
from apps.prediction_training.services.registry import activate_model


class Command(BaseCommand):
    help = 'Activate trained prediction model artifact.'

    def add_arguments(self, parser):
        parser.add_argument('artifact_id', type=int)

    def handle(self, *args, **options):
        artifact = PredictionModelArtifact.objects.filter(id=options['artifact_id']).first()
        if artifact is None:
            raise CommandError('Model artifact not found.')
        activate_model(artifact=artifact)
        self.stdout.write(self.style.SUCCESS(f'Activated model artifact id={artifact.id} name={artifact.name} version={artifact.version}'))
