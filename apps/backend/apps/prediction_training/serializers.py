from rest_framework import serializers

from apps.prediction_training.models import PredictionDatasetRun, PredictionModelArtifact, PredictionTrainingRun


class PredictionDatasetBuildRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default='default_dataset')
    horizon_hours = serializers.IntegerField(required=False, min_value=1, default=24)


class PredictionTrainingRunRequestSerializer(serializers.Serializer):
    dataset_run_id = serializers.IntegerField(min_value=1)
    model_name = serializers.CharField(required=False, allow_blank=True, default='xgboost_baseline')


class PredictionDatasetRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionDatasetRun
        fields = '__all__'


class PredictionTrainingRunSerializer(serializers.ModelSerializer):
    dataset_run = PredictionDatasetRunSerializer(read_only=True)

    class Meta:
        model = PredictionTrainingRun
        fields = '__all__'


class PredictionModelArtifactSerializer(serializers.ModelSerializer):
    training_run = PredictionTrainingRunSerializer(read_only=True)

    class Meta:
        model = PredictionModelArtifact
        fields = '__all__'
