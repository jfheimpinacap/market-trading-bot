from django.urls import path

from apps.opportunity_supervisor import views

app_name = 'opportunity_supervisor'

urlpatterns = [
    path('run-cycle/', views.OpportunityRunCycleView.as_view(), name='run-cycle'),
    path('cycles/', views.OpportunityCycleListView.as_view(), name='cycle-list'),
    path('cycles/<int:pk>/', views.OpportunityCycleDetailView.as_view(), name='cycle-detail'),
    path('items/', views.OpportunityItemListView.as_view(), name='item-list'),
    path('summary/', views.OpportunitySummaryView.as_view(), name='summary'),
]
