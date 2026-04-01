from django.urls import path

from apps.research_agent.views import (
    ScanAgentConsensusRecommendationListView,
    ScanAgentConsensusRecordDetailView,
    ScanAgentConsensusRecordListView,
    ScanAgentConsensusRunListView,
    ScanAgentConsensusRunView,
    ScanAgentConsensusSummaryView,
    ScanAgentClusterListView,
    ScanAgentDivergenceRecordListView,
    ScanAgentHandoffPriorityDetailView,
    ScanAgentHandoffPriorityListView,
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
    path('run-consensus-review/', ScanAgentConsensusRunView.as_view(), name='run-consensus-review'),
    path('consensus-runs/', ScanAgentConsensusRunListView.as_view(), name='consensus-runs'),
    path('consensus-records/', ScanAgentConsensusRecordListView.as_view(), name='consensus-records'),
    path('consensus-records/<int:pk>/', ScanAgentConsensusRecordDetailView.as_view(), name='consensus-record-detail'),
    path('market-divergence-records/', ScanAgentDivergenceRecordListView.as_view(), name='market-divergence-records'),
    path('research-handoff-priorities/', ScanAgentHandoffPriorityListView.as_view(), name='research-handoff-priorities'),
    path('research-handoff-priorities/<int:pk>/', ScanAgentHandoffPriorityDetailView.as_view(), name='research-handoff-priority-detail'),
    path('consensus-recommendations/', ScanAgentConsensusRecommendationListView.as_view(), name='consensus-recommendations'),
    path('consensus-summary/', ScanAgentConsensusSummaryView.as_view(), name='consensus-summary'),
]
