from rest_framework import serializers

from apps.operator_alerts.models import OperatorAlert, OperatorDigest


class OperatorAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorAlert
        fields = '__all__'


class OperatorDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorDigest
        fields = '__all__'


class BuildDigestSerializer(serializers.Serializer):
    digest_type = serializers.ChoiceField(choices=['daily', 'session', 'manual', 'cycle_window'], required=False, default='session')
    window_start = serializers.DateTimeField(required=False)
    window_end = serializers.DateTimeField(required=False)
