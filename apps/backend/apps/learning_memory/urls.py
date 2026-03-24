from django.urls import path

from apps.learning_memory.views import (
    LearningAdjustmentListView,
    LearningMemoryDetailView,
    LearningMemoryListView,
    LearningRebuildView,
    LearningRebuildRunDetailView,
    LearningRebuildRunListView,
    LearningIntegrationStatusView,
    LearningSummaryView,
)

urlpatterns = [
    path('memory/', LearningMemoryListView.as_view(), name='memory-list'),
    path('memory/<int:pk>/', LearningMemoryDetailView.as_view(), name='memory-detail'),
    path('adjustments/', LearningAdjustmentListView.as_view(), name='adjustment-list'),
    path('summary/', LearningSummaryView.as_view(), name='summary'),
    path('rebuild/', LearningRebuildView.as_view(), name='rebuild'),
    path('rebuild-runs/', LearningRebuildRunListView.as_view(), name='rebuild-run-list'),
    path('rebuild-runs/<int:pk>/', LearningRebuildRunDetailView.as_view(), name='rebuild-run-detail'),
    path('integration-status/', LearningIntegrationStatusView.as_view(), name='integration-status'),
]
