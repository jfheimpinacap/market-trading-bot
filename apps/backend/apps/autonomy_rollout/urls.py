from django.urls import path

from apps.autonomy_rollout.views import (
    AutonomyRolloutRunDetailView,
    AutonomyRolloutRunListView,
    AutonomyRolloutSummaryView,
    EvaluateAutonomyRolloutView,
    RollbackAutonomyRolloutView,
    StartAutonomyRolloutView,
)

app_name = 'autonomy_rollout'

urlpatterns = [
    path('start/', StartAutonomyRolloutView.as_view(), name='start'),
    path('runs/', AutonomyRolloutRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', AutonomyRolloutRunDetailView.as_view(), name='run-detail'),
    path('runs/<int:pk>/evaluate/', EvaluateAutonomyRolloutView.as_view(), name='evaluate'),
    path('runs/<int:pk>/rollback/', RollbackAutonomyRolloutView.as_view(), name='rollback'),
    path('summary/', AutonomyRolloutSummaryView.as_view(), name='summary'),
]
