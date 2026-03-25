from django.urls import path

from apps.real_market_ops.views import (
    RealMarketEligibleMarketsView,
    RealMarketOpsEvaluateView,
    RealMarketOpsRunDetailView,
    RealMarketOpsRunListView,
    RealMarketOpsRunView,
    RealMarketOpsStatusView,
)

urlpatterns = [
    path('evaluate/', RealMarketOpsEvaluateView.as_view(), name='evaluate'),
    path('run/', RealMarketOpsRunView.as_view(), name='run'),
    path('runs/', RealMarketOpsRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', RealMarketOpsRunDetailView.as_view(), name='run-detail'),
    path('status/', RealMarketOpsStatusView.as_view(), name='status'),
    path('eligible-markets/', RealMarketEligibleMarketsView.as_view(), name='eligible-markets'),
]
