from django.urls import path

from apps.autonomy_recovery.views import (
    AutonomyRecoveryCandidatesView,
    AutonomyRecoveryRecommendationsView,
    AutonomyRecoveryRequestCloseApprovalView,
    AutonomyRecoveryRequestResumeApprovalView,
    AutonomyRecoveryRunReviewView,
    AutonomyRecoverySnapshotsByCampaignView,
    AutonomyRecoverySnapshotsView,
    AutonomyRecoverySummaryView,
)

app_name = 'autonomy_recovery'

urlpatterns = [
    path('candidates/', AutonomyRecoveryCandidatesView.as_view(), name='candidates'),
    path('run-review/', AutonomyRecoveryRunReviewView.as_view(), name='run_review'),
    path('snapshots/', AutonomyRecoverySnapshotsView.as_view(), name='snapshots'),
    path('snapshots/<int:campaign_id>/', AutonomyRecoverySnapshotsByCampaignView.as_view(), name='snapshots_by_campaign'),
    path('recommendations/', AutonomyRecoveryRecommendationsView.as_view(), name='recommendations'),
    path('summary/', AutonomyRecoverySummaryView.as_view(), name='summary'),
    path('request-resume-approval/<int:campaign_id>/', AutonomyRecoveryRequestResumeApprovalView.as_view(), name='request_resume_approval'),
    path('request-close-approval/<int:campaign_id>/', AutonomyRecoveryRequestCloseApprovalView.as_view(), name='request_close_approval'),
]
