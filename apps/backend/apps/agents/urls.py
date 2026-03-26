from django.urls import path

from apps.agents.views import (
    AgentDefinitionListView,
    AgentHandoffListView,
    AgentPipelineRunDetailView,
    AgentPipelineRunListView,
    AgentRunDetailView,
    AgentRunListView,
    AgentRunPipelineView,
    AgentSummaryView,
)

app_name = 'agents'

urlpatterns = [
    path('', AgentDefinitionListView.as_view(), name='agent-list'),
    path('runs/', AgentRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', AgentRunDetailView.as_view(), name='run-detail'),
    path('run-pipeline/', AgentRunPipelineView.as_view(), name='run-pipeline'),
    path('pipelines/', AgentPipelineRunListView.as_view(), name='pipeline-list'),
    path('pipelines/<int:pk>/', AgentPipelineRunDetailView.as_view(), name='pipeline-detail'),
    path('handoffs/', AgentHandoffListView.as_view(), name='handoff-list'),
    path('summary/', AgentSummaryView.as_view(), name='summary'),
]
