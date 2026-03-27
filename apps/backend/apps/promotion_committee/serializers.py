from rest_framework import serializers

from apps.champion_challenger.serializers import StackProfileBindingSerializer
from apps.promotion_committee.models import PromotionDecisionLog, PromotionReviewRun, StackEvidenceSnapshot


class StackEvidenceSnapshotSerializer(serializers.ModelSerializer):
    champion_binding = StackProfileBindingSerializer(read_only=True)
    challenger_binding = StackProfileBindingSerializer(read_only=True)

    class Meta:
        model = StackEvidenceSnapshot
        fields = '__all__'


class PromotionDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionDecisionLog
        fields = '__all__'


class PromotionReviewRunSerializer(serializers.ModelSerializer):
    evidence_snapshot = StackEvidenceSnapshotSerializer(read_only=True)
    decision_logs = PromotionDecisionLogSerializer(read_only=True, many=True)

    class Meta:
        model = PromotionReviewRun
        fields = '__all__'


class PromotionReviewRequestSerializer(serializers.Serializer):
    decision_mode = serializers.ChoiceField(
        choices=['RECOMMENDATION_ONLY', 'MANUAL_APPLY'], default='RECOMMENDATION_ONLY', required=False
    )
    challenger_binding_id = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.DictField(required=False)


class PromotionApplyRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
