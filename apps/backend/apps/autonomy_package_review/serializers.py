from rest_framework import serializers

from apps.autonomy_package_review.models import PackageResolution, PackageReviewRecommendation, PackageReviewRun


class PackageResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageResolution
        fields = '__all__'


class PackageReviewRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageReviewRecommendation
        fields = '__all__'


class PackageReviewRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageReviewRun
        fields = '__all__'


class PackageReviewActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
    rationale = serializers.CharField(required=False, allow_blank=True, max_length=255)
    reason_codes = serializers.ListField(required=False, child=serializers.CharField(max_length=64), allow_empty=True)
