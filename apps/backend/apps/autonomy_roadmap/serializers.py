from rest_framework import serializers

from apps.autonomy_roadmap.models import AutonomyRoadmapPlan, DomainDependency, DomainRoadmapProfile, RoadmapBundle, RoadmapRecommendation


class DomainRoadmapProfileSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)

    class Meta:
        model = DomainRoadmapProfile
        fields = '__all__'


class DomainDependencySerializer(serializers.ModelSerializer):
    source_domain_slug = serializers.CharField(source='source_domain.slug', read_only=True)
    target_domain_slug = serializers.CharField(source='target_domain.slug', read_only=True)
    source_criticality = serializers.CharField(source='source_domain.roadmap_profile.criticality', read_only=True)
    target_criticality = serializers.CharField(source='target_domain.roadmap_profile.criticality', read_only=True)

    class Meta:
        model = DomainDependency
        fields = '__all__'


class RoadmapRecommendationSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source='domain.slug', read_only=True)
    plan_id = serializers.IntegerField(source='plan.id', read_only=True)

    class Meta:
        model = RoadmapRecommendation
        fields = '__all__'


class RoadmapBundleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapBundle
        fields = '__all__'


class AutonomyRoadmapPlanSerializer(serializers.ModelSerializer):
    recommendations = RoadmapRecommendationSerializer(many=True, read_only=True)
    bundles = RoadmapBundleSerializer(many=True, read_only=True)

    class Meta:
        model = AutonomyRoadmapPlan
        fields = '__all__'


class RunRoadmapPlanSerializer(serializers.Serializer):
    requested_by = serializers.CharField(required=False, allow_blank=True)
