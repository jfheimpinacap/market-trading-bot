from django.urls import path

from apps.autonomy_intake.views import (
    AutonomyIntakeAcknowledgeView,
    AutonomyIntakeCandidatesView,
    AutonomyIntakeEmitView,
    AutonomyIntakeProposalDetailView,
    AutonomyIntakeProposalsView,
    AutonomyIntakeRecommendationsView,
    AutonomyIntakeRunReviewView,
    AutonomyIntakeSummaryView,
)

app_name = 'autonomy_intake'

urlpatterns = [
    path('candidates/', AutonomyIntakeCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyIntakeRunReviewView.as_view(), name='run_review'),
    path('proposals/', AutonomyIntakeProposalsView.as_view(), name='proposals'),
    path('proposals/<int:proposal_id>/', AutonomyIntakeProposalDetailView.as_view(), name='proposal_detail'),
    path('recommendations/', AutonomyIntakeRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyIntakeSummaryView.as_view(), name='summary'),
    path('emit/<int:backlog_item_id>/', AutonomyIntakeEmitView.as_view(), name='emit'),
    path('acknowledge/<int:proposal_id>/', AutonomyIntakeAcknowledgeView.as_view(), name='acknowledge'),
]
