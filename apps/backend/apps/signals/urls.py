from django.urls import path

from apps.signals.views import (
    MarketSignalDetailView,
    MarketSignalListView,
    MockAgentListView,
    OpportunitySignalListView,
    RunFusionToProposalView,
    RunSignalFusionView,
    SignalBoardSummaryView,
    SignalFusionRunDetailView,
    SignalFusionRunListView,
    SignalSummaryView,
)

app_name = 'signals'

urlpatterns = [
    path('agents/', MockAgentListView.as_view(), name='signal-agent-list'),
    path('summary/', SignalSummaryView.as_view(), name='signal-summary'),
    path('run-fusion/', RunSignalFusionView.as_view(), name='signal-run-fusion'),
    path('runs/', SignalFusionRunListView.as_view(), name='signal-fusion-run-list'),
    path('runs/<int:pk>/', SignalFusionRunDetailView.as_view(), name='signal-fusion-run-detail'),
    path('opportunities/', OpportunitySignalListView.as_view(), name='signal-opportunities'),
    path('board-summary/', SignalBoardSummaryView.as_view(), name='signal-board-summary'),
    path('run-to-proposal/', RunFusionToProposalView.as_view(), name='signal-run-to-proposal'),
    path('', MarketSignalListView.as_view(), name='signal-list'),
    path('<int:pk>/', MarketSignalDetailView.as_view(), name='signal-detail'),
]
