from django.urls import path

from apps.automation_demo.views import (
    DemoAutomationRunDetailView,
    DemoAutomationRunListView,
    DemoAutomationSummaryView,
    GenerateSignalsView,
    GenerateTradeReviewsView,
    RebuildLearningMemoryView,
    RevaluePortfolioView,
    RunDemoCycleView,
    RunFullLearningCycleView,
    SimulateTickView,
    SyncDemoStateView,
)

urlpatterns = [
    path('simulate-tick/', SimulateTickView.as_view(), name='simulate-tick'),
    path('generate-signals/', GenerateSignalsView.as_view(), name='generate-signals'),
    path('revalue-portfolio/', RevaluePortfolioView.as_view(), name='revalue-portfolio'),
    path('generate-trade-reviews/', GenerateTradeReviewsView.as_view(), name='generate-trade-reviews'),
    path('sync-demo-state/', SyncDemoStateView.as_view(), name='sync-demo-state'),
    path('rebuild-learning-memory/', RebuildLearningMemoryView.as_view(), name='rebuild-learning-memory'),
    path('run-demo-cycle/', RunDemoCycleView.as_view(), name='run-demo-cycle'),
    path('run-full-learning-cycle/', RunFullLearningCycleView.as_view(), name='run-full-learning-cycle'),
    path('runs/', DemoAutomationRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', DemoAutomationRunDetailView.as_view(), name='run-detail'),
    path('summary/', DemoAutomationSummaryView.as_view(), name='summary'),
]
