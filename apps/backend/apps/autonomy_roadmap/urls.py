from django.urls import path

from apps.autonomy_roadmap.views import (
    AutonomyRoadmapPlanDetailView,
    AutonomyRoadmapPlanListView,
    AutonomyRoadmapSummaryView,
    DomainDependencyListView,
    RoadmapRecommendationListView,
    RunAutonomyRoadmapPlanView,
)

app_name = 'autonomy_roadmap'

urlpatterns = [
    path('dependencies/', DomainDependencyListView.as_view(), name='dependencies'),
    path('run-plan/', RunAutonomyRoadmapPlanView.as_view(), name='run-plan'),
    path('plans/', AutonomyRoadmapPlanListView.as_view(), name='plans'),
    path('plans/<int:pk>/', AutonomyRoadmapPlanDetailView.as_view(), name='plan-detail'),
    path('recommendations/', RoadmapRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyRoadmapSummaryView.as_view(), name='summary'),
]
