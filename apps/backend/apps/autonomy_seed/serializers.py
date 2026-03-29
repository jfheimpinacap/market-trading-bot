from rest_framework import serializers

from apps.autonomy_seed.models import GovernanceSeed, SeedRecommendation, SeedRun


class GovernanceSeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceSeed
        fields = '__all__'


class SeedRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedRecommendation
        fields = '__all__'


class SeedRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeedRun
        fields = '__all__'


class SeedActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
