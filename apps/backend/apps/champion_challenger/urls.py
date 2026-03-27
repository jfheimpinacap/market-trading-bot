from django.urls import path

from apps.champion_challenger.views import (
    ChampionChallengerRunCreateView,
    ChampionChallengerRunDetailView,
    ChampionChallengerRunListView,
    ChampionChallengerSummaryView,
    CurrentChampionBindingView,
    SetChampionBindingView,
)

app_name = 'champion_challenger'

urlpatterns = [
    path('run/', ChampionChallengerRunCreateView.as_view(), name='run'),
    path('runs/', ChampionChallengerRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', ChampionChallengerRunDetailView.as_view(), name='run-detail'),
    path('current-champion/', CurrentChampionBindingView.as_view(), name='current-champion'),
    path('summary/', ChampionChallengerSummaryView.as_view(), name='summary'),
    path('set-champion-binding/', SetChampionBindingView.as_view(), name='set-champion-binding'),
]
