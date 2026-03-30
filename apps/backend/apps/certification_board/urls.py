from django.urls import path

from apps.certification_board.views import (
    CertificationCandidateListView,
    CertificationDecisionListView,
    CertificationEvidencePackListView,
    CertificationApplyView,
    CertificationRecommendationListView,
    CertificationRunDetailView,
    CertificationRunListView,
    CertificationRunReviewView,
    CertificationSummaryView,
    CurrentCertificationView,
    PostRolloutCertificationSummaryView,
    RunPostRolloutCertificationReviewView,
)

urlpatterns = [
    path('run-review/', CertificationRunReviewView.as_view(), name='run-review'),
    path('runs/', CertificationRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', CertificationRunDetailView.as_view(), name='run-detail'),
    path('current/', CurrentCertificationView.as_view(), name='current'),
    path('summary/', CertificationSummaryView.as_view(), name='summary'),
    path('apply/<int:pk>/', CertificationApplyView.as_view(), name='apply'),
    path('run-post-rollout-review/', RunPostRolloutCertificationReviewView.as_view(), name='run-post-rollout-review'),
    path('candidates/', CertificationCandidateListView.as_view(), name='candidates'),
    path('evidence-packs/', CertificationEvidencePackListView.as_view(), name='evidence-packs'),
    path('decisions/', CertificationDecisionListView.as_view(), name='decisions'),
    path('recommendations/', CertificationRecommendationListView.as_view(), name='recommendations'),
    path('post-rollout-summary/', PostRolloutCertificationSummaryView.as_view(), name='post-rollout-summary'),
]
