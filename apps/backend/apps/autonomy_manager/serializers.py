from rest_framework import serializers

from apps.autonomy_manager.models import (
    AutonomyDomain,
    AutonomyEnvelope,
    AutonomyStageRecommendation,
    AutonomyStageState,
    AutonomyStageTransition,
)
from apps.autonomy_manager.services.envelopes import build_envelope_payload


class AutonomyEnvelopeSerializer(serializers.ModelSerializer):
    envelope = serializers.SerializerMethodField()

    class Meta:
        model = AutonomyEnvelope
        fields = ['id', 'domain', 'envelope']

    def get_envelope(self, obj: AutonomyEnvelope) -> dict:
        return build_envelope_payload(obj)


class AutonomyDomainSerializer(serializers.ModelSerializer):
    envelope = serializers.SerializerMethodField()

    class Meta:
        model = AutonomyDomain
        fields = '__all__'

    def get_envelope(self, obj: AutonomyDomain) -> dict | None:
        if not hasattr(obj, 'envelope'):
            return None
        return build_envelope_payload(obj.envelope)


class AutonomyStageStateSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = AutonomyStageState
        fields = '__all__'


class AutonomyStageTransitionSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)

    class Meta:
        model = AutonomyStageTransition
        fields = '__all__'


class AutonomyStageRecommendationSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)
    transition = serializers.SerializerMethodField()

    class Meta:
        model = AutonomyStageRecommendation
        fields = '__all__'

    def get_transition(self, obj: AutonomyStageRecommendation) -> dict | None:
        transition = obj.transitions.order_by('-created_at', '-id').first()
        if not transition:
            return None
        return AutonomyStageTransitionSerializer(transition).data


class AutonomyApplyTransitionSerializer(serializers.Serializer):
    applied_by = serializers.CharField(required=False, allow_blank=True)


class AutonomyRollbackTransitionSerializer(serializers.Serializer):
    rolled_back_by = serializers.CharField(required=False, allow_blank=True)


class AutonomyRunReviewSerializer(serializers.Serializer):
    requested_by = serializers.CharField(required=False, allow_blank=True)
