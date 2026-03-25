from django.urls import path

from apps.replay_lab.views import ReplayRunDetailView, ReplayRunListView, ReplayRunStepsView, ReplayRunView, ReplaySummaryView

urlpatterns = [
    path('run/', ReplayRunView.as_view(), name='run'),
    path('runs/', ReplayRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', ReplayRunDetailView.as_view(), name='run-detail'),
    path('runs/<int:pk>/steps/', ReplayRunStepsView.as_view(), name='run-steps'),
    path('summary/', ReplaySummaryView.as_view(), name='summary'),
]
