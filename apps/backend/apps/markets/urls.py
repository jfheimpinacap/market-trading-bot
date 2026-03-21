from django.urls import path

from .views import EventListView, MarketDetailView, MarketListView, MarketSystemSummaryView, ProviderListView

app_name = 'markets'

urlpatterns = [
    path('providers/', ProviderListView.as_view(), name='provider-list'),
    path('events/', EventListView.as_view(), name='event-list'),
    path('system-summary/', MarketSystemSummaryView.as_view(), name='market-system-summary'),
    path('', MarketListView.as_view(), name='market-list'),
    path('<int:pk>/', MarketDetailView.as_view(), name='market-detail'),
]
