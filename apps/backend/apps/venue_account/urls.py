from django.urls import path

from apps.venue_account.views import (
    VenueAccountBalancesView,
    VenueAccountCurrentView,
    VenueAccountOrdersView,
    VenueAccountPositionsView,
    VenueAccountReconciliationRunDetailView,
    VenueAccountReconciliationRunsView,
    VenueAccountRunReconciliationView,
    VenueAccountSummaryView,
)

app_name = 'venue_account'

urlpatterns = [
    path('current/', VenueAccountCurrentView.as_view(), name='current'),
    path('orders/', VenueAccountOrdersView.as_view(), name='orders'),
    path('positions/', VenueAccountPositionsView.as_view(), name='positions'),
    path('balances/', VenueAccountBalancesView.as_view(), name='balances'),
    path('run-reconciliation/', VenueAccountRunReconciliationView.as_view(), name='run-reconciliation'),
    path('reconciliation-runs/', VenueAccountReconciliationRunsView.as_view(), name='reconciliation-runs'),
    path('reconciliation-runs/<int:pk>/', VenueAccountReconciliationRunDetailView.as_view(), name='reconciliation-run-detail'),
    path('summary/', VenueAccountSummaryView.as_view(), name='summary'),
]
