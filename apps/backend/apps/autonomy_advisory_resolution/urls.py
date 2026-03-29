from django.urls import path

from apps.autonomy_advisory_resolution.views import (
    AutonomyAdvisoryResolutionAdoptView,
    AutonomyAdvisoryResolutionAcknowledgeView,
    AutonomyAdvisoryResolutionCandidatesView,
    AutonomyAdvisoryResolutionDeferredView,
    AutonomyAdvisoryResolutionListView,
    AutonomyAdvisoryResolutionRecommendationListView,
    AutonomyAdvisoryResolutionRejectView,
    AutonomyAdvisoryResolutionRunReviewView,
    AutonomyAdvisoryResolutionSummaryView,
)

app_name = 'autonomy_advisory_resolution'

urlpatterns = [
    path('candidates/', AutonomyAdvisoryResolutionCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyAdvisoryResolutionRunReviewView.as_view(), name='run_review'),
    path('resolutions/', AutonomyAdvisoryResolutionListView.as_view(), name='resolutions'),
    path('recommendations/', AutonomyAdvisoryResolutionRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyAdvisoryResolutionSummaryView.as_view(), name='summary'),
    path('acknowledge/<int:artifact_id>/', AutonomyAdvisoryResolutionAcknowledgeView.as_view(), name='acknowledge'),
    path('adopt/<int:artifact_id>/', AutonomyAdvisoryResolutionAdoptView.as_view(), name='adopt'),
    path('defer/<int:artifact_id>/', AutonomyAdvisoryResolutionDeferredView.as_view(), name='defer'),
    path('reject/<int:artifact_id>/', AutonomyAdvisoryResolutionRejectView.as_view(), name='reject'),
]
