from django.urls import path

from apps.signals.views import MarketSignalDetailView, MarketSignalListView, MockAgentListView, SignalSummaryView

app_name = 'signals'

urlpatterns = [
    path('agents/', MockAgentListView.as_view(), name='signal-agent-list'),
    path('summary/', SignalSummaryView.as_view(), name='signal-summary'),
    path('', MarketSignalListView.as_view(), name='signal-list'),
    path('<int:pk>/', MarketSignalDetailView.as_view(), name='signal-detail'),
]
