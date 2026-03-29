from django.urls import path

from apps.autonomy_package_review.views import (
    AutonomyPackageResolutionDetailView,
    AutonomyPackageResolutionListView,
    AutonomyPackageReviewAcknowledgeView,
    AutonomyPackageReviewAdoptView,
    AutonomyPackageReviewCandidatesView,
    AutonomyPackageReviewDeferView,
    AutonomyPackageReviewRecommendationListView,
    AutonomyPackageReviewRejectView,
    AutonomyPackageReviewRunView,
    AutonomyPackageReviewSummaryView,
)

app_name = 'autonomy_package_review'

urlpatterns = [
    path('candidates/', AutonomyPackageReviewCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyPackageReviewRunView.as_view(), name='run_review'),
    path('resolutions/', AutonomyPackageResolutionListView.as_view(), name='resolutions'),
    path('resolutions/<int:resolution_id>/', AutonomyPackageResolutionDetailView.as_view(), name='resolution_detail'),
    path('recommendations/', AutonomyPackageReviewRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyPackageReviewSummaryView.as_view(), name='summary'),
    path('acknowledge/<int:package_id>/', AutonomyPackageReviewAcknowledgeView.as_view(), name='acknowledge'),
    path('adopt/<int:package_id>/', AutonomyPackageReviewAdoptView.as_view(), name='adopt'),
    path('defer/<int:package_id>/', AutonomyPackageReviewDeferView.as_view(), name='defer'),
    path('reject/<int:package_id>/', AutonomyPackageReviewRejectView.as_view(), name='reject'),
]
