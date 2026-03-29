from django.urls import path

from apps.autonomy_scheduler.views import (
    AutonomySchedulerAdmitView,
    AutonomySchedulerDeferView,
    AutonomySchedulerQueueView,
    AutonomySchedulerRecommendationsView,
    AutonomySchedulerRunPlanView,
    AutonomySchedulerSummaryView,
    AutonomySchedulerWindowsView,
)

app_name = 'autonomy_scheduler'

urlpatterns = [
    path('queue/', AutonomySchedulerQueueView.as_view(), name='queue'),
    path('windows/', AutonomySchedulerWindowsView.as_view(), name='windows'),
    path('run-plan/', AutonomySchedulerRunPlanView.as_view(), name='run_plan'),
    path('recommendations/', AutonomySchedulerRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomySchedulerSummaryView.as_view(), name='summary'),
    path('admit/<int:campaign_id>/', AutonomySchedulerAdmitView.as_view(), name='admit'),
    path('defer/<int:campaign_id>/', AutonomySchedulerDeferView.as_view(), name='defer'),
]
