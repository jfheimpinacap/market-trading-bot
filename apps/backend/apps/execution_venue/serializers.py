from rest_framework import serializers

from apps.execution_venue.models import VenueCapabilityProfile, VenueOrderPayload, VenueOrderResponse, VenueParityRun


class VenueCapabilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueCapabilityProfile
        fields = '__all__'


class VenueOrderPayloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueOrderPayload
        fields = '__all__'


class VenueOrderResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueOrderResponse
        fields = '__all__'


class VenueParityRunSerializer(serializers.ModelSerializer):
    payload = VenueOrderPayloadSerializer(read_only=True)
    response = VenueOrderResponseSerializer(read_only=True)

    class Meta:
        model = VenueParityRun
        fields = '__all__'


class VenueActionMetadataSerializer(serializers.Serializer):
    metadata = serializers.DictField(required=False)
