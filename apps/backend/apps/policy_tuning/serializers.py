from rest_framework import serializers

from apps.policy_tuning.models import PolicyChangeSet, PolicyTuningApplicationLog, PolicyTuningCandidate, PolicyTuningReview


class PolicyChangeSetSerializer(serializers.ModelSerializer):
    diff = serializers.SerializerMethodField()

    class Meta:
        model = PolicyChangeSet
        fields = '__all__'

    def get_diff(self, obj: PolicyChangeSet) -> dict:
        return {
            'trust_tier': {'current': obj.old_trust_tier, 'proposed': obj.new_trust_tier},
            'conditions': {'current': obj.old_conditions, 'proposed': obj.new_conditions},
        }


class PolicyTuningReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyTuningReview
        fields = '__all__'


class PolicyTuningApplicationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyTuningApplicationLog
        fields = '__all__'


class PolicyTuningCandidateSerializer(serializers.ModelSerializer):
    change_set = PolicyChangeSetSerializer(read_only=True)
    reviews = PolicyTuningReviewSerializer(many=True, read_only=True)
    application_logs = PolicyTuningApplicationLogSerializer(many=True, read_only=True)

    class Meta:
        model = PolicyTuningCandidate
        fields = '__all__'


class CreatePolicyTuningCandidateSerializer(serializers.Serializer):
    recommendation_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['DRAFT', 'PENDING_APPROVAL'], required=False)


class PolicyTuningReviewRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVE', 'REJECT', 'REQUIRE_MORE_EVIDENCE', 'DEFER'])
    reviewer_note = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class ApplyPolicyTuningCandidateSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)
