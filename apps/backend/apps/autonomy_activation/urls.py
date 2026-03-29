from django.urls import path

from apps.autonomy_activation.views import (
    AutonomyActivationActivationsView,
    AutonomyActivationCandidatesView,
    AutonomyActivationDispatchView,
    AutonomyActivationRecommendationsView,
    AutonomyActivationRunDispatchReviewView,
    AutonomyActivationSummaryView,
)

app_name = 'autonomy_activation'

urlpatterns = [
    path('candidates/', AutonomyActivationCandidatesView.as_view(), name='candidates'),
    path('run-dispatch-review/', AutonomyActivationRunDispatchReviewView.as_view(), name='run_dispatch_review'),
    path('recommendations/', AutonomyActivationRecommendationsView.as_view(), name='recommendations'),
    path('activations/', AutonomyActivationActivationsView.as_view(), name='activations'),
    path('summary/', AutonomyActivationSummaryView.as_view(), name='summary'),
    path('dispatch/<int:campaign_id>/', AutonomyActivationDispatchView.as_view(), name='dispatch'),
]
