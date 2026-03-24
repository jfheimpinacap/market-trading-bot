from rest_framework import serializers

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun


class EvaluationMetricSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationMetricSet
        fields = '__all__'


class EvaluationRunSerializer(serializers.ModelSerializer):
    metric_set = EvaluationMetricSetSerializer(read_only=True)

    class Meta:
        model = EvaluationRun
        fields = '__all__'
