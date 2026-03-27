from rest_framework import serializers

from apps.champion_challenger.models import ChampionChallengerRun, ShadowComparisonResult, StackProfileBinding


class StackProfileBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackProfileBinding
        fields = '__all__'


class ShadowComparisonResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShadowComparisonResult
        fields = '__all__'


class ChampionChallengerRunSerializer(serializers.ModelSerializer):
    champion_binding = StackProfileBindingSerializer(read_only=True)
    challenger_binding = StackProfileBindingSerializer(read_only=True)
    comparison_result = ShadowComparisonResultSerializer(read_only=True)

    class Meta:
        model = ChampionChallengerRun
        fields = '__all__'


class ChampionChallengerRunRequestSerializer(serializers.Serializer):
    challenger_name = serializers.CharField(required=False, default='challenger_shadow')
    challenger_overrides = serializers.DictField(required=False, default=dict)
    lookback_hours = serializers.IntegerField(required=False, min_value=1, max_value=24 * 14, default=24)
    provider_scope = serializers.CharField(required=False, default='all')
    source_scope = serializers.ChoiceField(required=False, choices=['real_only', 'demo_only', 'mixed'], default='mixed')
    start_timestamp = serializers.DateTimeField(required=False)
    end_timestamp = serializers.DateTimeField(required=False)


class SetChampionBindingSerializer(serializers.Serializer):
    binding_id = serializers.IntegerField(min_value=1)
