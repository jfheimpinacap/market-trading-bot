from rest_framework import serializers

from apps.autonomy_planning_review.models import PlanningProposalResolution, PlanningReviewRecommendation, PlanningReviewRun


class PlanningProposalResolutionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = PlanningProposalResolution
        fields = '__all__'


class PlanningReviewRecommendationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='planning_proposal.campaign.title', read_only=True)

    class Meta:
        model = PlanningReviewRecommendation
        fields = '__all__'


class PlanningReviewRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanningReviewRun
        fields = '__all__'


class PlanningReviewActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
    rationale = serializers.CharField(required=False, allow_blank=True, max_length=255)
    reason_codes = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
