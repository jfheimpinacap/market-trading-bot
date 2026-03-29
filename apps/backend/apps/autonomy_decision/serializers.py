from rest_framework import serializers

from apps.autonomy_decision.models import DecisionRecommendation, DecisionRun, GovernanceDecision


class GovernanceDecisionSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = GovernanceDecision
        fields = '__all__'


class DecisionRecommendationSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='planning_proposal.campaign.title', read_only=True)

    class Meta:
        model = DecisionRecommendation
        fields = '__all__'


class DecisionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionRun
        fields = '__all__'


class DecisionActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
