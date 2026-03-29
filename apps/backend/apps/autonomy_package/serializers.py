from rest_framework import serializers

from apps.autonomy_package.models import GovernancePackage, PackageRecommendation, PackageRun


class GovernancePackageSerializer(serializers.ModelSerializer):
    linked_decision_ids = serializers.SerializerMethodField()

    class Meta:
        model = GovernancePackage
        fields = '__all__'

    def get_linked_decision_ids(self, obj: GovernancePackage) -> list[int]:
        return list(obj.linked_decisions.values_list('id', flat=True))


class PackageRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageRecommendation
        fields = '__all__'


class PackageRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageRun
        fields = '__all__'


class PackageActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, allow_blank=True, default='operator-ui', max_length=120)
