from django.urls import path

from apps.learning_memory.views import (
    ActivatePostmortemLearningAdjustmentView,
    ExpirePostmortemLearningAdjustmentView,
    FailurePatternListView,
    LearningAdjustmentListView,
    LearningApplicationRecordListView,
    LearningIntegrationStatusView,
    LearningMemoryDetailView,
    LearningMemoryListView,
    LearningRecommendationListView,
    LearningRebuildRunDetailView,
    LearningRebuildRunListView,
    LearningRebuildView,
    LearningSummaryView,
    PostmortemLearningAdjustmentDetailView,
    PostmortemLearningAdjustmentListView,
    PostmortemLearningLoopSummaryView,
    RunPostmortemLearningLoopView,
)

urlpatterns = [
    path('memory/', LearningMemoryListView.as_view(), name='memory-list'),
    path('memory/<int:pk>/', LearningMemoryDetailView.as_view(), name='memory-detail'),
    path('legacy-adjustments/', LearningAdjustmentListView.as_view(), name='legacy-adjustment-list'),
    path('summary/', LearningSummaryView.as_view(), name='summary'),
    path('rebuild/', LearningRebuildView.as_view(), name='rebuild'),
    path('rebuild-runs/', LearningRebuildRunListView.as_view(), name='rebuild-run-list'),
    path('rebuild-runs/<int:pk>/', LearningRebuildRunDetailView.as_view(), name='rebuild-run-detail'),
    path('integration-status/', LearningIntegrationStatusView.as_view(), name='integration-status'),

    path('run-postmortem-loop/', RunPostmortemLearningLoopView.as_view(), name='run-postmortem-loop'),
    path('failure-patterns/', FailurePatternListView.as_view(), name='failure-patterns'),
    path('adjustments/', PostmortemLearningAdjustmentListView.as_view(), name='adjustments'),
    path('adjustments/<int:pk>/', PostmortemLearningAdjustmentDetailView.as_view(), name='adjustment-detail'),
    path('adjustments/<int:pk>/activate/', ActivatePostmortemLearningAdjustmentView.as_view(), name='activate-adjustment'),
    path('adjustments/<int:pk>/expire/', ExpirePostmortemLearningAdjustmentView.as_view(), name='expire-adjustment'),
    path('application-records/', LearningApplicationRecordListView.as_view(), name='application-records'),
    path('recommendations/', LearningRecommendationListView.as_view(), name='recommendations'),
    path('postmortem-loop-summary/', PostmortemLearningLoopSummaryView.as_view(), name='postmortem-loop-summary'),
]
