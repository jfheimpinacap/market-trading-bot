from django.urls import path

from apps.autonomy_feedback.views import (
    AutonomyFeedbackCandidatesView,
    AutonomyFeedbackCompleteView,
    AutonomyFeedbackRecommendationsView,
    AutonomyFeedbackResolutionsView,
    AutonomyFeedbackRunReviewView,
    AutonomyFeedbackSummaryView,
)

app_name = 'autonomy_feedback'

urlpatterns = [
    path('candidates/', AutonomyFeedbackCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyFeedbackRunReviewView.as_view(), name='run_review'),
    path('resolutions/', AutonomyFeedbackResolutionsView.as_view(), name='resolutions'),
    path('recommendations/', AutonomyFeedbackRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyFeedbackSummaryView.as_view(), name='summary'),
    path('complete/<int:followup_id>/', AutonomyFeedbackCompleteView.as_view(), name='complete'),
]
