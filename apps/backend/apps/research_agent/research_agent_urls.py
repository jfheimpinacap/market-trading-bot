from django.urls import path

from apps.research_agent.views import (
    ResearchAgentCandidateListView,
    ResearchAgentRecommendationListView,
    ResearchAgentTriageDecisionListView,
    ResearchAgentUniverseScanRunView,
    ResearchAgentUniverseSummaryView,
)

app_name = 'research_agent_v2'

urlpatterns = [
    path('run-universe-scan/', ResearchAgentUniverseScanRunView.as_view(), name='run-universe-scan'),
    path('candidates/', ResearchAgentCandidateListView.as_view(), name='candidates'),
    path('triage-decisions/', ResearchAgentTriageDecisionListView.as_view(), name='triage-decisions'),
    path('recommendations/', ResearchAgentRecommendationListView.as_view(), name='recommendations'),
    path('universe-summary/', ResearchAgentUniverseSummaryView.as_view(), name='universe-summary'),
]
