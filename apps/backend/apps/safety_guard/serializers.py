from rest_framework import serializers

from apps.safety_guard.models import SafetyEvent, SafetyPolicyConfig


class SafetyEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyEvent
        fields = [
            'id',
            'event_type',
            'severity',
            'source',
            'related_session_id',
            'related_cycle_id',
            'related_market_id',
            'related_trade_id',
            'message',
            'details',
            'created_at',
            'updated_at',
        ]


class SafetyPolicyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyPolicyConfig
        exclude = []
        read_only_fields = ['id', 'name', 'created_at', 'updated_at']
