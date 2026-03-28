from rest_framework import serializers

from apps.autonomy_scenario.models import AutonomyScenarioRun, ScenarioOption, ScenarioRecommendation, ScenarioRiskEstimate


class ScenarioOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScenarioOption
        fields = '__all__'


class ScenarioRiskEstimateSerializer(serializers.ModelSerializer):
    option_key = serializers.CharField(source='option.option_key', read_only=True)

    class Meta:
        model = ScenarioRiskEstimate
        fields = '__all__'


class ScenarioRecommendationSerializer(serializers.ModelSerializer):
    option_key = serializers.CharField(source='option.option_key', read_only=True)

    class Meta:
        model = ScenarioRecommendation
        fields = '__all__'


class AutonomyScenarioRunSerializer(serializers.ModelSerializer):
    options = ScenarioOptionSerializer(many=True, read_only=True)
    risk_estimates = ScenarioRiskEstimateSerializer(many=True, read_only=True)
    recommendations = ScenarioRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = AutonomyScenarioRun
        fields = '__all__'


class RunAutonomyScenarioSerializer(serializers.Serializer):
    requested_by = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
