from django.urls import path

from apps.safety_guard.views import (
    SafetyConfigView,
    SafetyEventDetailView,
    SafetyEventListView,
    SafetyKillSwitchDisableView,
    SafetyKillSwitchEnableView,
    SafetyResetCooldownView,
    SafetyStatusView,
    SafetySummaryView,
)

app_name = 'safety_guard'

urlpatterns = [
    path('status/', SafetyStatusView.as_view(), name='status'),
    path('events/', SafetyEventListView.as_view(), name='events'),
    path('events/<int:pk>/', SafetyEventDetailView.as_view(), name='event-detail'),
    path('kill-switch/enable/', SafetyKillSwitchEnableView.as_view(), name='kill-switch-enable'),
    path('kill-switch/disable/', SafetyKillSwitchDisableView.as_view(), name='kill-switch-disable'),
    path('reset-cooldown/', SafetyResetCooldownView.as_view(), name='reset-cooldown'),
    path('config/', SafetyConfigView.as_view(), name='config'),
    path('summary/', SafetySummaryView.as_view(), name='summary'),
]
