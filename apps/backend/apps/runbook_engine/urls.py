from django.urls import path

from apps.runbook_engine.views import (
    RunbookCompleteView,
    RunbookCreateView,
    RunbookDetailView,
    RunbookListView,
    RunbookRecommendationsView,
    RunbookRunStepView,
    RunbookSummaryView,
    RunbookTemplateListView,
)

app_name = 'runbook_engine'

urlpatterns = [
    path('templates/', RunbookTemplateListView.as_view(), name='templates'),
    path('', RunbookListView.as_view(), name='list'),
    path('summary/', RunbookSummaryView.as_view(), name='summary'),
    path('recommendations/', RunbookRecommendationsView.as_view(), name='recommendations'),
    path('create/', RunbookCreateView.as_view(), name='create'),
    path('<int:pk>/', RunbookDetailView.as_view(), name='detail'),
    path('<int:pk>/run-step/<int:step_id>/', RunbookRunStepView.as_view(), name='run-step'),
    path('<int:pk>/complete/', RunbookCompleteView.as_view(), name='complete'),
]
