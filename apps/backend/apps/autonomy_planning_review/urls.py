from django.urls import path

from apps.autonomy_planning_review.views import (
    AutonomyPlanningReviewAcknowledgeView,
    AutonomyPlanningReviewAcceptView,
    AutonomyPlanningReviewCandidatesView,
    AutonomyPlanningReviewDeferView,
    AutonomyPlanningReviewRecommendationListView,
    AutonomyPlanningReviewRejectView,
    AutonomyPlanningReviewResolutionDetailView,
    AutonomyPlanningReviewResolutionListView,
    AutonomyPlanningReviewRunReviewView,
    AutonomyPlanningReviewSummaryView,
)

app_name = 'autonomy_planning_review'

urlpatterns = [
    path('candidates/', AutonomyPlanningReviewCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyPlanningReviewRunReviewView.as_view(), name='run_review'),
    path('resolutions/', AutonomyPlanningReviewResolutionListView.as_view(), name='resolutions'),
    path('resolutions/<int:resolution_id>/', AutonomyPlanningReviewResolutionDetailView.as_view(), name='resolution_detail'),
    path('recommendations/', AutonomyPlanningReviewRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyPlanningReviewSummaryView.as_view(), name='summary'),
    path('acknowledge/<int:proposal_id>/', AutonomyPlanningReviewAcknowledgeView.as_view(), name='acknowledge'),
    path('accept/<int:proposal_id>/', AutonomyPlanningReviewAcceptView.as_view(), name='accept'),
    path('defer/<int:proposal_id>/', AutonomyPlanningReviewDeferView.as_view(), name='defer'),
    path('reject/<int:proposal_id>/', AutonomyPlanningReviewRejectView.as_view(), name='reject'),
]
