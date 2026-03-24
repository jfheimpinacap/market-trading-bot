from django.urls import path

from apps.learning_memory.views import (
    LearningAdjustmentListView,
    LearningMemoryDetailView,
    LearningMemoryListView,
    LearningRebuildView,
    LearningSummaryView,
)

urlpatterns = [
    path('memory/', LearningMemoryListView.as_view(), name='memory-list'),
    path('memory/<int:pk>/', LearningMemoryDetailView.as_view(), name='memory-detail'),
    path('adjustments/', LearningAdjustmentListView.as_view(), name='adjustment-list'),
    path('summary/', LearningSummaryView.as_view(), name='summary'),
    path('rebuild/', LearningRebuildView.as_view(), name='rebuild'),
]
