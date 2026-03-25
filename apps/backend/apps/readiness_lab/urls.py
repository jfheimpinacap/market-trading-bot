from django.urls import path

from apps.readiness_lab.views import (
    ReadinessAssessView,
    ReadinessProfileDetailView,
    ReadinessProfileListView,
    ReadinessRunDetailView,
    ReadinessRunListView,
    ReadinessSeedProfilesView,
    ReadinessSummaryView,
)

urlpatterns = [
    path('profiles/', ReadinessProfileListView.as_view(), name='profiles'),
    path('profiles/<int:pk>/', ReadinessProfileDetailView.as_view(), name='profile-detail'),
    path('assess/', ReadinessAssessView.as_view(), name='assess'),
    path('runs/', ReadinessRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', ReadinessRunDetailView.as_view(), name='run-detail'),
    path('summary/', ReadinessSummaryView.as_view(), name='summary'),
    path('seed-profiles/', ReadinessSeedProfilesView.as_view(), name='seed-profiles'),
]
