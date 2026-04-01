from django.urls import path

from apps.research_agent.views import (
    ResearchAgentCandidateListView,
    ResearchAgentPredictionHandoffListView,
    ResearchAgentPursuitRecommendationListView,
    ResearchAgentPursuitRunListView,
    ResearchAgentPursuitScoreListView,
    ResearchAgentPursuitSummaryView,
    ResearchAgentRecommendationListView,
    ResearchAgentRunPursuitReviewView,
    ResearchAgentStructuralAssessmentListView,
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
    path('run-pursuit-review/', ResearchAgentRunPursuitReviewView.as_view(), name='run-pursuit-review'),
    path('pursuit-runs/', ResearchAgentPursuitRunListView.as_view(), name='pursuit-runs'),
    path('structural-assessments/', ResearchAgentStructuralAssessmentListView.as_view(), name='structural-assessments'),
    path('pursuit-scores/', ResearchAgentPursuitScoreListView.as_view(), name='pursuit-scores'),
    path('prediction-handoffs/', ResearchAgentPredictionHandoffListView.as_view(), name='prediction-handoffs'),
    path('pursuit-recommendations/', ResearchAgentPursuitRecommendationListView.as_view(), name='pursuit-recommendations'),
    path('pursuit-summary/', ResearchAgentPursuitSummaryView.as_view(), name='pursuit-summary'),
]
