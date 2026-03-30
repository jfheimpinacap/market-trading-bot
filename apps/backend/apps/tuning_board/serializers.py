from rest_framework import serializers

from apps.tuning_board.models import TuningImpactHypothesis, TuningProposal, TuningProposalBundle, TuningRecommendation, TuningReviewRun


class TuningReviewRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TuningReviewRun
        fields = '__all__'


class TuningProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TuningProposal
        fields = '__all__'


class TuningImpactHypothesisSerializer(serializers.ModelSerializer):
    class Meta:
        model = TuningImpactHypothesis
        fields = '__all__'


class TuningRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TuningRecommendation
        fields = '__all__'


class TuningProposalBundleSerializer(serializers.ModelSerializer):
    linked_proposals = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = TuningProposalBundle
        fields = '__all__'


class TuningRunReviewRequestSerializer(serializers.Serializer):
    evaluation_run_id = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.JSONField(required=False)
