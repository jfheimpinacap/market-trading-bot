from rest_framework import serializers

from apps.connector_lab.models import AdapterQualificationResult, AdapterQualificationRun, AdapterReadinessRecommendation, ConnectorFixtureProfile


class ConnectorFixtureProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorFixtureProfile
        fields = '__all__'


class AdapterQualificationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdapterQualificationResult
        fields = '__all__'


class AdapterReadinessRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdapterReadinessRecommendation
        fields = '__all__'


class AdapterQualificationRunSerializer(serializers.ModelSerializer):
    results = AdapterQualificationResultSerializer(many=True, read_only=True)
    readiness_recommendation = AdapterReadinessRecommendationSerializer(read_only=True)
    fixture_profile = ConnectorFixtureProfileSerializer(read_only=True)

    class Meta:
        model = AdapterQualificationRun
        fields = '__all__'


class RunQualificationRequestSerializer(serializers.Serializer):
    fixture_profile = serializers.SlugField(required=False)
    metadata = serializers.DictField(required=False)
