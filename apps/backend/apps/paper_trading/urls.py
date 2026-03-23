from django.urls import path

from .views import (
    PaperAccountView,
    PaperPortfolioSnapshotListView,
    PaperPositionListView,
    PaperRevalueView,
    PaperSummaryView,
    PaperTradeListCreateView,
)

app_name = 'paper_trading'

urlpatterns = [
    path('account/', PaperAccountView.as_view(), name='paper-account'),
    path('positions/', PaperPositionListView.as_view(), name='paper-position-list'),
    path('trades/', PaperTradeListCreateView.as_view(), name='paper-trade-list-create'),
    path('summary/', PaperSummaryView.as_view(), name='paper-summary'),
    path('revalue/', PaperRevalueView.as_view(), name='paper-revalue'),
    path('snapshots/', PaperPortfolioSnapshotListView.as_view(), name='paper-snapshot-list'),
]
