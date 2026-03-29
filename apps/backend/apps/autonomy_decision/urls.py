from django.urls import path

from apps.autonomy_decision.views import (
    AutonomyDecisionAcknowledgeView,
    AutonomyDecisionCandidatesView,
    AutonomyDecisionListView,
    AutonomyDecisionRecommendationListView,
    AutonomyDecisionRegisterView,
    AutonomyDecisionRunReviewView,
    AutonomyDecisionSummaryView,
)

app_name = 'autonomy_decision'

urlpatterns = [
    path('candidates/', AutonomyDecisionCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyDecisionRunReviewView.as_view(), name='run_review'),
    path('decisions/', AutonomyDecisionListView.as_view(), name='decisions'),
    path('recommendations/', AutonomyDecisionRecommendationListView.as_view(), name='recommendations'),
    path('summary/', AutonomyDecisionSummaryView.as_view(), name='summary'),
    path('register/<int:proposal_id>/', AutonomyDecisionRegisterView.as_view(), name='register'),
    path('acknowledge/<int:decision_id>/', AutonomyDecisionAcknowledgeView.as_view(), name='acknowledge'),
]
