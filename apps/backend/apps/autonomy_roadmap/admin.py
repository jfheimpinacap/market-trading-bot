from django.contrib import admin

from apps.autonomy_roadmap.models import AutonomyRoadmapPlan, DomainDependency, DomainRoadmapProfile, RoadmapBundle, RoadmapRecommendation

admin.site.register(DomainDependency)
admin.site.register(DomainRoadmapProfile)
admin.site.register(AutonomyRoadmapPlan)
admin.site.register(RoadmapRecommendation)
admin.site.register(RoadmapBundle)
