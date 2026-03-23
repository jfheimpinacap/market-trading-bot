from django.urls import path

from apps.policy_engine.views import ApprovalDecisionListView, EvaluateTradePolicyView, PolicyDecisionSummaryView

app_name = 'policy_engine'

urlpatterns = [
    path('evaluate-trade/', EvaluateTradePolicyView.as_view(), name='evaluate-trade'),
    path('decisions/', ApprovalDecisionListView.as_view(), name='decision-list'),
    path('summary/', PolicyDecisionSummaryView.as_view(), name='summary'),
]
