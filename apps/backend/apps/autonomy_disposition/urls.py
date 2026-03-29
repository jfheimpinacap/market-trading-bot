from django.urls import path

from apps.autonomy_disposition.views import (
    AutonomyDispositionApplyView,
    AutonomyDispositionCandidatesView,
    AutonomyDispositionListView,
    AutonomyDispositionRecommendationsView,
    AutonomyDispositionRequestApprovalView,
    AutonomyDispositionRunReviewView,
    AutonomyDispositionSummaryView,
)

app_name = 'autonomy_disposition'

urlpatterns = [
    path('candidates/', AutonomyDispositionCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyDispositionRunReviewView.as_view(), name='run_review'),
    path('recommendations/', AutonomyDispositionRecommendationsView.as_view(), name='recommendations'),
    path('dispositions/', AutonomyDispositionListView.as_view(), name='dispositions'),
    path('summary/', AutonomyDispositionSummaryView.as_view(), name='summary'),
    path('request-approval/<int:campaign_id>/', AutonomyDispositionRequestApprovalView.as_view(), name='request_approval'),
    path('apply/<int:campaign_id>/', AutonomyDispositionApplyView.as_view(), name='apply'),
]
