from rest_framework import serializers

from apps.autonomy_intake.models import IntakeRecommendation, IntakeRun, PlanningProposal


class PlanningProposalSerializer(serializers.ModelSerializer):
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)

    class Meta:
        model = PlanningProposal
        fields = '__all__'


class IntakeRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntakeRecommendation
        fields = '__all__'


class IntakeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntakeRun
        fields = '__all__'


class IntakeActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
