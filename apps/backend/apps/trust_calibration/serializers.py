from rest_framework import serializers

from apps.trust_calibration.models import AutomationFeedbackSnapshot, TrustCalibrationRecommendation, TrustCalibrationRun


class TrustCalibrationRunRequestSerializer(serializers.Serializer):
    window_days = serializers.IntegerField(required=False, min_value=1, max_value=365, default=30)
    source_type = serializers.CharField(required=False, allow_blank=True, max_length=80)
    runbook_template_slug = serializers.CharField(required=False, allow_blank=True, max_length=120)
    profile_slug = serializers.CharField(required=False, allow_blank=True, max_length=80)
    include_degraded = serializers.BooleanField(required=False, default=True)


class TrustCalibrationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCalibrationRun
        fields = '__all__'


class AutomationFeedbackSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationFeedbackSnapshot
        fields = '__all__'


class TrustCalibrationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustCalibrationRecommendation
        fields = '__all__'
