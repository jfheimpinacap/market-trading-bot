from django.urls import path

from apps.memory_retrieval.views import (
    MemoryDocumentListView,
    MemoryIndexView,
    MemoryPrecedentSummaryView,
    MemoryRetrievalRunDetailView,
    MemoryRetrievalRunListView,
    MemoryRetrieveView,
    MemorySummaryView,
)

app_name = 'memory_retrieval'

urlpatterns = [
    path('index/', MemoryIndexView.as_view(), name='index'),
    path('retrieve/', MemoryRetrieveView.as_view(), name='retrieve'),
    path('documents/', MemoryDocumentListView.as_view(), name='documents'),
    path('retrieval-runs/', MemoryRetrievalRunListView.as_view(), name='retrieval-runs'),
    path('retrieval-runs/<int:pk>/', MemoryRetrievalRunDetailView.as_view(), name='retrieval-run-detail'),
    path('summary/', MemorySummaryView.as_view(), name='summary'),
    path('precedent-summary/', MemoryPrecedentSummaryView.as_view(), name='precedent-summary'),
]
