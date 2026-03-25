from django.urls import path

app_name = 'research_agent'

from apps.research_agent.views import (
    NarrativeItemDetailView,
    NarrativeItemListView,
    ResearchCandidateListView,
    ResearchRunAnalysisView,
    ResearchRunIngestView,
    ResearchSourceListCreateView,
    ResearchSummaryView,
)

urlpatterns = [
    path('sources/', ResearchSourceListCreateView.as_view(), name='source-list-create'),
    path('run-ingest/', ResearchRunIngestView.as_view(), name='run-ingest'),
    path('run-analysis/', ResearchRunAnalysisView.as_view(), name='run-analysis'),
    path('items/', NarrativeItemListView.as_view(), name='item-list'),
    path('items/<int:pk>/', NarrativeItemDetailView.as_view(), name='item-detail'),
    path('candidates/', ResearchCandidateListView.as_view(), name='candidate-list'),
    path('summary/', ResearchSummaryView.as_view(), name='summary'),
]
