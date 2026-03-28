from django.urls import path

from apps.policy_tuning.views import (
    PolicyTuningApplicationLogListView,
    PolicyTuningApplyView,
    PolicyTuningCandidateDetailView,
    PolicyTuningCandidateListView,
    PolicyTuningCreateCandidateView,
    PolicyTuningReviewView,
    PolicyTuningSummaryView,
)

urlpatterns = [
    path('create-candidate/', PolicyTuningCreateCandidateView.as_view(), name='create-candidate'),
    path('candidates/', PolicyTuningCandidateListView.as_view(), name='candidates'),
    path('candidates/<int:pk>/', PolicyTuningCandidateDetailView.as_view(), name='candidate-detail'),
    path('candidates/<int:pk>/review/', PolicyTuningReviewView.as_view(), name='candidate-review'),
    path('candidates/<int:pk>/apply/', PolicyTuningApplyView.as_view(), name='candidate-apply'),
    path('application-logs/', PolicyTuningApplicationLogListView.as_view(), name='application-logs'),
    path('summary/', PolicyTuningSummaryView.as_view(), name='summary'),
]
