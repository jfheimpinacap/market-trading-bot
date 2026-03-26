from django.urls import path

app_name = 'research_agent'

from apps.research_agent.views import (
    NarrativeItemDetailView,
    NarrativeItemListView,
    PursuitCandidateListView,
    ResearchBoardSummaryView,
    ResearchCandidateListView,
    ResearchRunAnalysisView,
    ResearchRunFullScanView,
    ResearchRunIngestView,
    ResearchRunUniverseScanView,
    ResearchSourceListCreateView,
    ResearchSummaryView,
    ResearchTriageToPredictionView,
    UniverseScanRunDetailView,
    UniverseScanRunListView,
)

urlpatterns = [
    path('sources/', ResearchSourceListCreateView.as_view(), name='source-list-create'),
    path('run-ingest/', ResearchRunIngestView.as_view(), name='run-ingest'),
    path('run-full-scan/', ResearchRunFullScanView.as_view(), name='run-full-scan'),
    path('run-analysis/', ResearchRunAnalysisView.as_view(), name='run-analysis'),
    path('run-universe-scan/', ResearchRunUniverseScanView.as_view(), name='run-universe-scan'),
    path('run-triage-to-prediction/', ResearchTriageToPredictionView.as_view(), name='run-triage-to-prediction'),
    path('universe-scans/', UniverseScanRunListView.as_view(), name='universe-scan-list'),
    path('universe-scans/<int:pk>/', UniverseScanRunDetailView.as_view(), name='universe-scan-detail'),
    path('items/', NarrativeItemListView.as_view(), name='item-list'),
    path('items/<int:pk>/', NarrativeItemDetailView.as_view(), name='item-detail'),
    path('candidates/', ResearchCandidateListView.as_view(), name='candidate-list'),
    path('pursuit-candidates/', PursuitCandidateListView.as_view(), name='pursuit-candidate-list'),
    path('board-summary/', ResearchBoardSummaryView.as_view(), name='board-summary'),
    path('summary/', ResearchSummaryView.as_view(), name='summary'),
]
