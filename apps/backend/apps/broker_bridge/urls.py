from django.urls import path

from apps.broker_bridge.views import (
    BrokerBridgeSummaryView,
    BrokerIntentCreateView,
    BrokerIntentDetailView,
    BrokerIntentDryRunView,
    BrokerIntentListView,
    BrokerIntentValidateView,
)

app_name = 'broker_bridge'

urlpatterns = [
    path('create-intent/', BrokerIntentCreateView.as_view(), name='create-intent'),
    path('validate/<int:pk>/', BrokerIntentValidateView.as_view(), name='validate-intent'),
    path('dry-run/<int:pk>/', BrokerIntentDryRunView.as_view(), name='dry-run-intent'),
    path('intents/', BrokerIntentListView.as_view(), name='intents'),
    path('intents/<int:pk>/', BrokerIntentDetailView.as_view(), name='intent-detail'),
    path('summary/', BrokerBridgeSummaryView.as_view(), name='summary'),
]
