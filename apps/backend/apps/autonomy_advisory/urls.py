from django.urls import path

from apps.autonomy_advisory.views import (
    AutonomyAdvisoryArtifactListView,
    AutonomyAdvisoryCandidatesView,
    AutonomyAdvisoryEmitView,
    AutonomyAdvisoryRecommendationListView,
    AutonomyAdvisoryRunReviewView,
    AutonomyAdvisorySummaryView,
)

app_name = 'autonomy_advisory'

urlpatterns = [
    path('candidates/', AutonomyAdvisoryCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyAdvisoryRunReviewView.as_view(), name='run_review'),
    path('artifacts/', AutonomyAdvisoryArtifactListView.as_view(), name='artifacts'),
    path('recommendations/', AutonomyAdvisoryRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyAdvisorySummaryView.as_view(), name='summary'),
    path('emit/<int:insight_id>/', AutonomyAdvisoryEmitView.as_view(), name='emit_insight'),
]
