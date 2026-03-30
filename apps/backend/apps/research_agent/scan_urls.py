from django.urls import path

from apps.research_agent.views import (
    ScanAgentClusterListView,
    ScanAgentRecommendationListView,
    ScanAgentRunView,
    ScanAgentSignalListView,
    ScanAgentSummaryView,
)

app_name = 'scan_agent'

urlpatterns = [
    path('run-scan/', ScanAgentRunView.as_view(), name='run-scan'),
    path('signals/', ScanAgentSignalListView.as_view(), name='signals'),
    path('clusters/', ScanAgentClusterListView.as_view(), name='clusters'),
    path('recommendations/', ScanAgentRecommendationListView.as_view(), name='recommendations'),
    path('summary/', ScanAgentSummaryView.as_view(), name='summary'),
]
