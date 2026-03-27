from django.urls import path

from apps.automation_policy.views import (
    AutomationActionLogListView,
    AutomationDecisionListView,
    AutomationPolicyApplyProfileView,
    AutomationPolicyCurrentView,
    AutomationPolicyEvaluateView,
    AutomationPolicyProfilesView,
    AutomationPolicySummaryView,
)

app_name = 'automation_policy'

urlpatterns = [
    path('profiles/', AutomationPolicyProfilesView.as_view(), name='profiles'),
    path('current/', AutomationPolicyCurrentView.as_view(), name='current'),
    path('evaluate/', AutomationPolicyEvaluateView.as_view(), name='evaluate'),
    path('decisions/', AutomationDecisionListView.as_view(), name='decisions'),
    path('action-logs/', AutomationActionLogListView.as_view(), name='action-logs'),
    path('apply-profile/', AutomationPolicyApplyProfileView.as_view(), name='apply-profile'),
    path('summary/', AutomationPolicySummaryView.as_view(), name='summary'),
]
