from rest_framework import serializers


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    environment = serializers.CharField()
    database_configured = serializers.BooleanField()
    redis_configured = serializers.BooleanField()
