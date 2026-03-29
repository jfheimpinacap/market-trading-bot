from django.urls import path

from apps.autonomy_launch.views import (
    AutonomyLaunchAuthorizeView,
    AutonomyLaunchAuthorizationsView,
    AutonomyLaunchCandidatesView,
    AutonomyLaunchHoldView,
    AutonomyLaunchReadinessView,
    AutonomyLaunchRecommendationsView,
    AutonomyLaunchRunPreflightView,
    AutonomyLaunchSummaryView,
)

app_name = 'autonomy_launch'

urlpatterns = [
    path('candidates/', AutonomyLaunchCandidatesView.as_view(), name='candidates'),
    path('run-preflight/', AutonomyLaunchRunPreflightView.as_view(), name='run_preflight'),
    path('readiness/', AutonomyLaunchReadinessView.as_view(), name='readiness'),
    path('recommendations/', AutonomyLaunchRecommendationsView.as_view(), name='recommendations'),
    path('authorizations/', AutonomyLaunchAuthorizationsView.as_view(), name='authorizations'),
    path('summary/', AutonomyLaunchSummaryView.as_view(), name='summary'),
    path('authorize/<int:campaign_id>/', AutonomyLaunchAuthorizeView.as_view(), name='authorize'),
    path('hold/<int:campaign_id>/', AutonomyLaunchHoldView.as_view(), name='hold'),
]
