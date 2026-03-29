from django.urls import path

from apps.autonomy_closeout.views import (
    AutonomyCloseoutCandidatesView,
    AutonomyCloseoutCompleteView,
    AutonomyCloseoutFindingsView,
    AutonomyCloseoutRecommendationsView,
    AutonomyCloseoutReportsView,
    AutonomyCloseoutRunReviewView,
    AutonomyCloseoutSummaryView,
)

app_name = 'autonomy_closeout'

urlpatterns = [
    path('candidates/', AutonomyCloseoutCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyCloseoutRunReviewView.as_view(), name='run_review'),
    path('reports/', AutonomyCloseoutReportsView.as_view(), name='reports'),
    path('findings/', AutonomyCloseoutFindingsView.as_view(), name='findings'),
    path('recommendations/', AutonomyCloseoutRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyCloseoutSummaryView.as_view(), name='summary'),
    path('complete/<int:campaign_id>/', AutonomyCloseoutCompleteView.as_view(), name='complete'),
]
