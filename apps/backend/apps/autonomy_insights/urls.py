from django.urls import path

from apps.autonomy_insights.views import (
    AutonomyInsightCandidatesView,
    AutonomyInsightDetailView,
    AutonomyInsightListView,
    AutonomyInsightMarkReviewedView,
    AutonomyInsightRecommendationsView,
    AutonomyInsightRunReviewView,
    AutonomyInsightSummaryView,
)

app_name = 'autonomy_insights'

urlpatterns = [
    path('candidates/', AutonomyInsightCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyInsightRunReviewView.as_view(), name='run_review'),
    path('insights/', AutonomyInsightListView.as_view(), name='insights'),
    path('recommendations/', AutonomyInsightRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyInsightSummaryView.as_view(), name='summary'),
    path('insights/<int:insight_id>/', AutonomyInsightDetailView.as_view(), name='insight_detail'),
    path('mark-reviewed/<int:insight_id>/', AutonomyInsightMarkReviewedView.as_view(), name='mark_reviewed'),
]
