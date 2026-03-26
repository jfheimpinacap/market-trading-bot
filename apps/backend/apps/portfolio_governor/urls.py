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
]
