from rest_framework import serializers

from apps.notification_center.models import NotificationDelivery
from apps.operator_alerts.models import OperatorAlert, OperatorDigest


class OperatorAlertSerializer(serializers.ModelSerializer):
    latest_notification_status = serializers.SerializerMethodField()
    latest_notification_channel = serializers.SerializerMethodField()

    class Meta:
        model = OperatorAlert
        fields = '__all__'

    def get_latest_notification_status(self, obj):
        latest = NotificationDelivery.objects.filter(related_alert=obj).order_by('-created_at', '-id').values('delivery_status').first()
        return latest['delivery_status'] if latest else None

    def get_latest_notification_channel(self, obj):
        latest = NotificationDelivery.objects.filter(related_alert=obj).select_related('channel').order_by('-created_at', '-id').first()
        return latest.channel.slug if latest and latest.channel else None


class OperatorDigestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorDigest
        fields = '__all__'


class BuildDigestSerializer(serializers.Serializer):
    digest_type = serializers.ChoiceField(choices=['daily', 'session', 'manual', 'cycle_window'], required=False, default='session')
    window_start = serializers.DateTimeField(required=False)
    window_end = serializers.DateTimeField(required=False)
