from django.urls import path

from apps.policy_rollout.views import (
    EvaluatePolicyRolloutView,
    PolicyRolloutRunDetailView,
    PolicyRolloutRunListView,
    PolicyRolloutSummaryView,
    RollbackPolicyRolloutView,
    StartPolicyRolloutView,
)

app_name = 'policy_rollout'

urlpatterns = [
    path('start/', StartPolicyRolloutView.as_view(), name='start'),
    path('runs/', PolicyRolloutRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', PolicyRolloutRunDetailView.as_view(), name='run-detail'),
    path('runs/<int:pk>/evaluate/', EvaluatePolicyRolloutView.as_view(), name='evaluate'),
    path('runs/<int:pk>/rollback/', RollbackPolicyRolloutView.as_view(), name='rollback'),
    path('summary/', PolicyRolloutSummaryView.as_view(), name='summary'),
]
