from django.urls import path

from apps.autonomy_campaign.views import (
    AbortAutonomyCampaignView,
    AutonomyCampaignDetailView,
    AutonomyCampaignListView,
    AutonomyCampaignSummaryView,
    CreateAutonomyCampaignView,
    ResumeAutonomyCampaignView,
    StartAutonomyCampaignView,
)

app_name = 'autonomy_campaign'

urlpatterns = [
    path('create/', CreateAutonomyCampaignView.as_view(), name='create'),
    path('', AutonomyCampaignListView.as_view(), name='list'),
    path('summary/', AutonomyCampaignSummaryView.as_view(), name='summary'),
    path('<int:pk>/', AutonomyCampaignDetailView.as_view(), name='detail'),
    path('<int:pk>/start/', StartAutonomyCampaignView.as_view(), name='start'),
    path('<int:pk>/resume/', ResumeAutonomyCampaignView.as_view(), name='resume'),
    path('<int:pk>/abort/', AbortAutonomyCampaignView.as_view(), name='abort'),
]
