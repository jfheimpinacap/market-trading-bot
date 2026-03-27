from django.urls import path

from apps.profile_manager import views

app_name = 'profile_manager'

urlpatterns = [
    path('run-governance/', views.RunProfileGovernanceView.as_view(), name='run-governance'),
    path('runs/', views.ProfileGovernanceRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', views.ProfileGovernanceRunDetailView.as_view(), name='run-detail'),
    path('current/', views.CurrentProfileGovernanceView.as_view(), name='current'),
    path('summary/', views.ProfileGovernanceSummaryView.as_view(), name='summary'),
    path('apply-decision/<int:decision_id>/', views.ApplyProfileDecisionView.as_view(), name='apply-decision'),
]
