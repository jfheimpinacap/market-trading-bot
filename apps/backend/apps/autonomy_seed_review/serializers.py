from rest_framework import serializers

from apps.autonomy_seed_review.models import SeedResolution, SeedReviewRecommendation, SeedReviewRun


class SeedResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedResolution
        fields = '__all__'


class SeedReviewRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedReviewRecommendation
        fields = '__all__'


class SeedReviewRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedReviewRun
        fields = '__all__'


class SeedReviewActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
