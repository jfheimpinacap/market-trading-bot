from rest_framework import serializers

from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile


class ReadinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadinessProfile
        fields = '__all__'


class ReadinessAssessmentRunSerializer(serializers.ModelSerializer):
    readiness_profile = ReadinessProfileSerializer(read_only=True)

    class Meta:
        model = ReadinessAssessmentRun
        fields = '__all__'


class ReadinessAssessmentRequestSerializer(serializers.Serializer):
    readiness_profile_id = serializers.IntegerField(min_value=1)
