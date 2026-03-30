from rest_framework import serializers

from apps.evaluation_lab.models import (
    CalibrationBucket,
    EffectivenessMetric,
    EvaluationMetricSet,
    EvaluationRecommendation,
    EvaluationRun,
    EvaluationRuntimeRun,
    OutcomeAlignmentRecord,
)


class EvaluationMetricSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationMetricSet
        fields = '__all__'


class EvaluationRunSerializer(serializers.ModelSerializer):
    metric_set = EvaluationMetricSetSerializer(read_only=True)

    class Meta:
        model = EvaluationRun
        fields = '__all__'


class EvaluationRuntimeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationRuntimeRun
        fields = '__all__'


class OutcomeAlignmentRecordSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)
    market_provider = serializers.CharField(source='linked_market.provider.slug', read_only=True)
    market_category = serializers.CharField(source='linked_market.category', read_only=True)

    class Meta:
        model = OutcomeAlignmentRecord
        fields = '__all__'


class CalibrationBucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalibrationBucket
        fields = '__all__'


class EffectivenessMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = EffectivenessMetric
        fields = '__all__'


class EvaluationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationRecommendation
        fields = '__all__'
