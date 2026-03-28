from rest_framework import serializers

from apps.approval_center.models import ApprovalDecision, ApprovalDecisionType, ApprovalRequest
from apps.approval_center.services.impact import get_approval_impact_preview


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDecision
        fields = '__all__'


class ApprovalRequestSerializer(serializers.ModelSerializer):
    decisions = ApprovalDecisionSerializer(many=True, read_only=True)
    impact_preview = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = '__all__'

    def get_impact_preview(self, obj: ApprovalRequest):
        return get_approval_impact_preview(obj)


class ApprovalDecisionInputSerializer(serializers.Serializer):
    rationale = serializers.CharField(required=False, allow_blank=True)
    decided_by = serializers.CharField(required=False, allow_blank=True, max_length=120, default='local-operator')
    metadata = serializers.JSONField(required=False)


class ApprovalDecisionResultSerializer(serializers.Serializer):
    approval = ApprovalRequestSerializer()


class ApprovalStatusFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(required=False, choices=[choice[0] for choice in ApprovalRequest._meta.get_field('status').choices])


class ApprovalDecisionTypeSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ApprovalDecisionType.values)
