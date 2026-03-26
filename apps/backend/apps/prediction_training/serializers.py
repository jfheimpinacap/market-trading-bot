from rest_framework import serializers

from apps.prediction_training.models import (
    ModelComparisonResult,
    ModelComparisonRun,
    ModelEvaluationProfile,
    PredictionDatasetRun,
    PredictionModelArtifact,
    PredictionTrainingRun,
)


class PredictionDatasetBuildRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default='default_dataset')
    horizon_hours = serializers.IntegerField(required=False, min_value=1, default=24)


class PredictionTrainingRunRequestSerializer(serializers.Serializer):
    dataset_run_id = serializers.IntegerField(min_value=1)
    model_name = serializers.CharField(required=False, allow_blank=True, default='xgboost_baseline')


class ModelCompareRequestSerializer(serializers.Serializer):
    baseline_key = serializers.CharField(required=False, allow_blank=True, default='heuristic_baseline')
    candidate_key = serializers.CharField(required=False, allow_blank=True, default='active_model')
    profile_slug = serializers.CharField(required=False, allow_blank=True, default='balanced_model_eval')
    scope = serializers.ChoiceField(choices=['demo_only', 'real_only', 'mixed'], required=False, default='mixed')
    dataset_run_id = serializers.IntegerField(required=False, min_value=1)
    replay_run_id = serializers.IntegerField(required=False, min_value=1)


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


class ModelEvaluationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelEvaluationProfile
        fields = '__all__'


class ModelComparisonResultSerializer(serializers.ModelSerializer):
    artifact = PredictionModelArtifactSerializer(read_only=True)

    class Meta:
        model = ModelComparisonResult
        fields = '__all__'


class ModelComparisonRunSerializer(serializers.ModelSerializer):
    evaluation_profile = ModelEvaluationProfileSerializer(read_only=True)
    dataset_run = PredictionDatasetRunSerializer(read_only=True)
    results = ModelComparisonResultSerializer(read_only=True, many=True)

    class Meta:
        model = ModelComparisonRun
        fields = '__all__'
