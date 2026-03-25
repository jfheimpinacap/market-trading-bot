from rest_framework import serializers

from apps.notification_center.models import NotificationChannel, NotificationDelivery, NotificationRule


class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = '__all__'


class NotificationRuleSerializer(serializers.ModelSerializer):
    channel_refs = serializers.PrimaryKeyRelatedField(queryset=NotificationChannel.objects.all(), source='channels', many=True, required=False)

    class Meta:
        model = NotificationRule
        fields = [
            'id',
            'name',
            'is_enabled',
            'match_criteria',
            'delivery_mode',
            'channel_refs',
            'severity_threshold',
            'cooldown_seconds',
            'dedupe_window_seconds',
            'created_at',
            'updated_at',
        ]


class NotificationDeliverySerializer(serializers.ModelSerializer):
    channel_slug = serializers.CharField(source='channel.slug', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = '__all__'


class TriggerSendSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
