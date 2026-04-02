from django.urls import path

from apps.portfolio_governor import views

app_name = 'portfolio_governor'

urlpatterns = [
    path('run-governance/', views.RunPortfolioGovernanceView.as_view(), name='run-governance'),
    path('runs/', views.PortfolioGovernanceRunListView.as_view(), name='run-list'),
    path('runs/<int:pk>/', views.PortfolioGovernanceRunDetailView.as_view(), name='run-detail'),
    path('exposure/', views.PortfolioExposureView.as_view(), name='exposure'),
    path('throttle/', views.PortfolioThrottleView.as_view(), name='throttle'),
    path('summary/', views.PortfolioGovernanceSummaryView.as_view(), name='summary'),
    path('run-exposure-coordination-review/', views.RunExposureCoordinationReviewView.as_view(), name='run-exposure-coordination-review'),
    path('exposure-coordination-runs/', views.ExposureCoordinationRunListView.as_view(), name='exposure-coordination-runs'),
    path('exposure-cluster-snapshots/', views.ExposureClusterSnapshotListView.as_view(), name='exposure-cluster-snapshots'),
    path('session-exposure-contributions/', views.SessionExposureContributionListView.as_view(), name='session-exposure-contributions'),
    path('exposure-conflict-reviews/', views.ExposureConflictReviewListView.as_view(), name='exposure-conflict-reviews'),
    path('exposure-decisions/', views.ExposureDecisionListView.as_view(), name='exposure-decisions'),
    path('exposure-recommendations/', views.ExposureRecommendationListView.as_view(), name='exposure-recommendations'),
    path('exposure-coordination-summary/', views.ExposureCoordinationSummaryView.as_view(), name='exposure-coordination-summary'),
]
