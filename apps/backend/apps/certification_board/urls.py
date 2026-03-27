from django.urls import path

from apps.certification_board.views import (
    CertificationApplyView,
    CertificationRunDetailView,
    CertificationRunListView,
    CertificationRunReviewView,
    CertificationSummaryView,
    CurrentCertificationView,
)

urlpatterns = [
    path('run-review/', CertificationRunReviewView.as_view(), name='run-review'),
    path('runs/', CertificationRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', CertificationRunDetailView.as_view(), name='run-detail'),
    path('current/', CurrentCertificationView.as_view(), name='current'),
    path('summary/', CertificationSummaryView.as_view(), name='summary'),
    path('apply/<int:pk>/', CertificationApplyView.as_view(), name='apply'),
]
