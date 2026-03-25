from django.urls import path

from apps.experiment_lab.views import (
    ExperimentComparisonView,
    ExperimentRunCreateView,
    ExperimentRunDetailView,
    ExperimentRunListView,
    ExperimentSummaryView,
    SeedStrategyProfilesView,
    StrategyProfileDetailView,
    StrategyProfileListView,
)

urlpatterns = [
    path('profiles/', StrategyProfileListView.as_view(), name='profiles'),
    path('profiles/<int:pk>/', StrategyProfileDetailView.as_view(), name='profile-detail'),
    path('run/', ExperimentRunCreateView.as_view(), name='run'),
    path('runs/', ExperimentRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', ExperimentRunDetailView.as_view(), name='run-detail'),
    path('comparison/', ExperimentComparisonView.as_view(), name='comparison'),
    path('summary/', ExperimentSummaryView.as_view(), name='summary'),
    path('seed-profiles/', SeedStrategyProfilesView.as_view(), name='seed-profiles'),
]
