from django.urls import path

from apps.promotion_committee.views import (
    CurrentPromotionRecommendationView,
    GovernedPromotionRunReviewView,
    GovernedPromotionSummaryView,
    PromotionApplyView,
    PromotionCasesView,
    PromotionDecisionRecommendationsView,
    PromotionEvidencePacksView,
    PromotionRunDetailView,
    PromotionRunListView,
    PromotionRunReviewView,
    PromotionSummaryView,
)

app_name = 'promotion_committee'

urlpatterns = [
    path('run-review/', GovernedPromotionRunReviewView.as_view(), name='governed-run-review'),
    path('cases/', PromotionCasesView.as_view(), name='cases'),
    path('evidence-packs/', PromotionEvidencePacksView.as_view(), name='evidence-packs'),
    path('recommendations/', PromotionDecisionRecommendationsView.as_view(), name='recommendations'),
    path('summary/', GovernedPromotionSummaryView.as_view(), name='governed-summary'),
    path('legacy-run-review/', PromotionRunReviewView.as_view(), name='run-review'),
    path('runs/', PromotionRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', PromotionRunDetailView.as_view(), name='run-detail'),
    path('current-recommendation/', CurrentPromotionRecommendationView.as_view(), name='current-recommendation'),
    path('legacy-summary/', PromotionSummaryView.as_view(), name='summary'),
    path('apply/<int:pk>/', PromotionApplyView.as_view(), name='apply'),
]
