from django.urls import path

from apps.rollout_manager.views import (
    CurrentRolloutView,
    RolloutCreatePlanView,
    RolloutEvaluateDecisionView,
    RolloutPauseView,
    RolloutResumeView,
    RolloutRollbackView,
    RolloutRunDetailView,
    RolloutRunListView,
    RolloutStartView,
    RolloutSummaryView,
)

app_name = 'rollout_manager'

urlpatterns = [
    path('create-plan/', RolloutCreatePlanView.as_view(), name='create-plan'),
    path('start/<int:pk>/', RolloutStartView.as_view(), name='start'),
    path('pause/<int:pk>/', RolloutPauseView.as_view(), name='pause'),
    path('resume/<int:pk>/', RolloutResumeView.as_view(), name='resume'),
    path('rollback/<int:pk>/', RolloutRollbackView.as_view(), name='rollback'),
    path('evaluate/<int:pk>/', RolloutEvaluateDecisionView.as_view(), name='evaluate'),
    path('runs/', RolloutRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', RolloutRunDetailView.as_view(), name='run-detail'),
    path('current/', CurrentRolloutView.as_view(), name='current'),
    path('summary/', RolloutSummaryView.as_view(), name='summary'),
]
