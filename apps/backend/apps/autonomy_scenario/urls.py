from django.urls import path

from apps.autonomy_scenario.views import (
    AutonomyScenarioOptionsView,
    AutonomyScenarioRecommendationListView,
    AutonomyScenarioRunDetailView,
    AutonomyScenarioRunListView,
    AutonomyScenarioSummaryView,
    RunAutonomyScenarioView,
)

app_name = 'autonomy_scenario'

urlpatterns = [
    path('run/', RunAutonomyScenarioView.as_view(), name='run'),
    path('runs/', AutonomyScenarioRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', AutonomyScenarioRunDetailView.as_view(), name='run-detail'),
    path('options/', AutonomyScenarioOptionsView.as_view(), name='options'),
    path('recommendations/', AutonomyScenarioRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyScenarioSummaryView.as_view(), name='summary'),
]
