from django.urls import path

from apps.postmortem_agents.views import (
    PostmortemBoardConclusionListView,
    PostmortemBoardReviewListView,
    PostmortemBoardRunApiView,
    PostmortemBoardRunDetailView,
    PostmortemBoardRunListView,
    PostmortemBoardSummaryView,
    PostmortemPrecedentCompareView,
)

app_name = 'postmortem_agents'

urlpatterns = [
    path('run/', PostmortemBoardRunApiView.as_view(), name='run'),
    path('runs/', PostmortemBoardRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', PostmortemBoardRunDetailView.as_view(), name='run-detail'),
    path('reviews/', PostmortemBoardReviewListView.as_view(), name='reviews'),
    path('conclusions/', PostmortemBoardConclusionListView.as_view(), name='conclusions'),
    path('summary/', PostmortemBoardSummaryView.as_view(), name='summary'),
    path('precedent-compare/', PostmortemPrecedentCompareView.as_view(), name='precedent-compare'),
]
