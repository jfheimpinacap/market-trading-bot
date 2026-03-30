from django.urls import path

from apps.opportunity_supervisor import views

app_name = 'opportunity_cycle'

urlpatterns = [
    path('run-review/', views.OpportunityCycleRunReviewView.as_view(), name='run-review'),
    path('candidates/', views.OpportunityCycleCandidateListView.as_view(), name='candidate-list'),
    path('assessments/', views.OpportunityCycleAssessmentListView.as_view(), name='assessment-list'),
    path('proposals/', views.OpportunityCycleProposalListView.as_view(), name='proposal-list'),
    path('recommendations/', views.OpportunityCycleRecommendationListView.as_view(), name='recommendation-list'),
    path('summary/', views.OpportunityCycleSummaryView.as_view(), name='cycle-runtime-summary'),
]
