from django.urls import path

from apps.autonomy_seed_review.views import (
    AutonomySeedReviewAcceptView,
    AutonomySeedReviewAcknowledgeView,
    AutonomySeedReviewCandidatesView,
    AutonomySeedReviewDeferView,
    AutonomySeedReviewRecommendationsView,
    AutonomySeedReviewRejectView,
    AutonomySeedReviewResolutionsView,
    AutonomySeedReviewRunView,
    AutonomySeedReviewSummaryView,
)

app_name = 'autonomy_seed_review'

urlpatterns = [
    path('candidates/', AutonomySeedReviewCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomySeedReviewRunView.as_view(), name='run_review'),
    path('resolutions/', AutonomySeedReviewResolutionsView.as_view(), name='resolutions'),
    path('recommendations/', AutonomySeedReviewRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomySeedReviewSummaryView.as_view(), name='summary'),
    path('acknowledge/<int:seed_id>/', AutonomySeedReviewAcknowledgeView.as_view(), name='acknowledge'),
    path('accept/<int:seed_id>/', AutonomySeedReviewAcceptView.as_view(), name='accept'),
    path('defer/<int:seed_id>/', AutonomySeedReviewDeferView.as_view(), name='defer'),
    path('reject/<int:seed_id>/', AutonomySeedReviewRejectView.as_view(), name='reject'),
]
