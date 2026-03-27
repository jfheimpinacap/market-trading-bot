from django.urls import path

from apps.promotion_committee.views import (
    CurrentPromotionRecommendationView,
    PromotionApplyView,
    PromotionRunDetailView,
    PromotionRunListView,
    PromotionRunReviewView,
    PromotionSummaryView,
)

app_name = 'promotion_committee'

urlpatterns = [
    path('run-review/', PromotionRunReviewView.as_view(), name='run-review'),
    path('runs/', PromotionRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', PromotionRunDetailView.as_view(), name='run-detail'),
    path('current-recommendation/', CurrentPromotionRecommendationView.as_view(), name='current-recommendation'),
    path('summary/', PromotionSummaryView.as_view(), name='summary'),
    path('apply/<int:pk>/', PromotionApplyView.as_view(), name='apply'),
]
