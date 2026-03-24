from django.urls import path

from apps.proposal_engine.views import GenerateTradeProposalView, TradeProposalDetailView, TradeProposalListView

app_name = 'proposal_engine'

urlpatterns = [
    path('', TradeProposalListView.as_view(), name='proposal-list'),
    path('<int:pk>/', TradeProposalDetailView.as_view(), name='proposal-detail'),
    path('generate/', GenerateTradeProposalView.as_view(), name='proposal-generate'),
]
