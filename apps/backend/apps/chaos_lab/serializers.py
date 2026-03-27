from rest_framework import serializers

from apps.chaos_lab.models import ChaosExperiment, ChaosObservation, ChaosRun, ResilienceBenchmark


class ChaosExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChaosExperiment
        fields = '__all__'


class ChaosObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChaosObservation
        fields = '__all__'


class ResilienceBenchmarkSerializer(serializers.ModelSerializer):
    experiment = ChaosExperimentSerializer(read_only=True)

    class Meta:
        model = ResilienceBenchmark
        fields = '__all__'


class ChaosRunSerializer(serializers.ModelSerializer):
    experiment = ChaosExperimentSerializer(read_only=True)
    observations = ChaosObservationSerializer(many=True, read_only=True)
    benchmark = ResilienceBenchmarkSerializer(read_only=True)

    class Meta:
        model = ChaosRun
        fields = '__all__'


class ChaosRunRequestSerializer(serializers.Serializer):
    experiment_id = serializers.IntegerField(min_value=1)
    trigger_mode = serializers.ChoiceField(required=False, choices=['manual', 'scheduled', 'benchmark_suite'], default='manual')
