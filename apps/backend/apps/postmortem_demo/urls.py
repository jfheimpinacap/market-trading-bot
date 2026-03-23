from django.urls import path

from apps.postmortem_demo.views import TradeReviewDetailView, TradeReviewListView, TradeReviewSummaryView

app_name = 'postmortem_demo'

urlpatterns = [
    path('summary/', TradeReviewSummaryView.as_view(), name='review-summary'),
    path('', TradeReviewListView.as_view(), name='review-list'),
    path('<int:pk>/', TradeReviewDetailView.as_view(), name='review-detail'),
]
