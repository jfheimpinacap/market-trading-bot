from django.urls import path

from apps.position_manager import views

app_name = 'position_manager'

urlpatterns = [
    path('run-lifecycle/', views.RunPositionLifecycleView.as_view(), name='run-lifecycle'),
    path('lifecycle-runs/', views.PositionLifecycleRunListView.as_view(), name='lifecycle-runs'),
    path('lifecycle-runs/<int:pk>/', views.PositionLifecycleRunDetailView.as_view(), name='lifecycle-run-detail'),
    path('decisions/', views.PositionLifecycleDecisionListView.as_view(), name='decisions'),
    path('summary/', views.PositionLifecycleSummaryView.as_view(), name='summary'),
]
