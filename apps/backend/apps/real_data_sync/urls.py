from django.urls import path

from apps.real_data_sync import views

urlpatterns = [
    path('run/', views.RealSyncRunView.as_view(), name='run'),
    path('runs/', views.RealSyncRunListView.as_view(), name='runs'),
    path('runs/<int:pk>/', views.RealSyncRunDetailView.as_view(), name='run-detail'),
    path('status/', views.RealSyncStatusView.as_view(), name='status'),
    path('summary/', views.RealSyncSummaryView.as_view(), name='summary'),
]
