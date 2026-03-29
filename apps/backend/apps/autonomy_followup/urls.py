from django.urls import path

from apps.autonomy_followup.views import (
    AutonomyFollowupCandidatesView,
    AutonomyFollowupEmitView,
    AutonomyFollowupListView,
    AutonomyFollowupRecommendationsView,
    AutonomyFollowupRunReviewView,
    AutonomyFollowupSummaryView,
)

app_name = 'autonomy_followup'

urlpatterns = [
    path('candidates/', AutonomyFollowupCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyFollowupRunReviewView.as_view(), name='run_review'),
    path('followups/', AutonomyFollowupListView.as_view(), name='followups'),
    path('recommendations/', AutonomyFollowupRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyFollowupSummaryView.as_view(), name='summary'),
    path('emit/<int:campaign_id>/', AutonomyFollowupEmitView.as_view(), name='emit'),
]
