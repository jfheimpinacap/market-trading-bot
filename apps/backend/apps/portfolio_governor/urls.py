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
    path('apply-exposure-decision/<int:decision_id>/', views.ApplyExposureDecisionView.as_view(), name='apply-exposure-decision'),
    path('run-exposure-apply-review/', views.RunExposureApplyReviewView.as_view(), name='run-exposure-apply-review'),
    path('exposure-coordination-runs/', views.ExposureCoordinationRunListView.as_view(), name='exposure-coordination-runs'),
    path('exposure-apply-runs/', views.ExposureApplyRunListView.as_view(), name='exposure-apply-runs'),
    path('exposure-cluster-snapshots/', views.ExposureClusterSnapshotListView.as_view(), name='exposure-cluster-snapshots'),
    path('session-exposure-contributions/', views.SessionExposureContributionListView.as_view(), name='session-exposure-contributions'),
    path('exposure-conflict-reviews/', views.ExposureConflictReviewListView.as_view(), name='exposure-conflict-reviews'),
    path('exposure-decisions/', views.ExposureDecisionListView.as_view(), name='exposure-decisions'),
    path('exposure-decisions/<int:pk>/', views.ExposureDecisionDetailView.as_view(), name='exposure-decision-detail'),
    path('exposure-recommendations/', views.ExposureRecommendationListView.as_view(), name='exposure-recommendations'),
    path('exposure-apply-targets/', views.ExposureApplyTargetListView.as_view(), name='exposure-apply-targets'),
    path('exposure-apply-decisions/', views.ExposureApplyDecisionListView.as_view(), name='exposure-apply-decisions'),
    path('exposure-apply-records/', views.ExposureApplyRecordListView.as_view(), name='exposure-apply-records'),
    path('exposure-apply-recommendations/', views.ExposureApplyRecommendationListView.as_view(), name='exposure-apply-recommendations'),
    path('exposure-coordination-summary/', views.ExposureCoordinationSummaryView.as_view(), name='exposure-coordination-summary'),
    path('exposure-apply-summary/', views.ExposureApplySummaryView.as_view(), name='exposure-apply-summary'),
]
