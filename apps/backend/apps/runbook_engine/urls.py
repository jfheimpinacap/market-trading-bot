from django.urls import path

from apps.runbook_engine.views import (
    RunbookApprovalCheckpointUpdateView,
    RunbookAutopilotRetryStepView,
    RunbookAutopilotRunDetailView,
    RunbookAutopilotRunListView,
    RunbookAutopilotRunStartView,
    RunbookAutopilotResumeView,
    RunbookAutopilotSummaryView,
    RunbookCompleteView,
    RunbookCreateView,
    RunbookDetailView,
    RunbookListView,
    RunbookRecommendationsView,
    RunbookRunStepView,
    RunbookSummaryView,
    RunbookTemplateListView,
)

app_name = 'runbook_engine'

urlpatterns = [
    path('templates/', RunbookTemplateListView.as_view(), name='templates'),
    path('', RunbookListView.as_view(), name='list'),
    path('summary/', RunbookSummaryView.as_view(), name='summary'),
    path('recommendations/', RunbookRecommendationsView.as_view(), name='recommendations'),
    path('create/', RunbookCreateView.as_view(), name='create'),
    path('autopilot-runs/', RunbookAutopilotRunListView.as_view(), name='autopilot-runs'),
    path('autopilot-runs/<int:pk>/', RunbookAutopilotRunDetailView.as_view(), name='autopilot-run-detail'),
    path('autopilot-runs/<int:pk>/resume/', RunbookAutopilotResumeView.as_view(), name='autopilot-resume'),
    path('autopilot-runs/<int:pk>/retry-step/<int:step_id>/', RunbookAutopilotRetryStepView.as_view(), name='autopilot-retry-step'),
    path('autopilot-summary/', RunbookAutopilotSummaryView.as_view(), name='autopilot-summary'),
    path('approval-checkpoints/<int:pk>/resolve/', RunbookApprovalCheckpointUpdateView.as_view(), name='approval-checkpoint-resolve'),
    path('<int:pk>/', RunbookDetailView.as_view(), name='detail'),
    path('<int:pk>/run-step/<int:step_id>/', RunbookRunStepView.as_view(), name='run-step'),
    path('<int:pk>/run-autopilot/', RunbookAutopilotRunStartView.as_view(), name='run-autopilot'),
    path('<int:pk>/complete/', RunbookCompleteView.as_view(), name='complete'),
]
