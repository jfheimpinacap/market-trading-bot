from django.urls import path

from apps.runtime_governor.views import RuntimeCapabilitiesView, RuntimeModesView, RuntimeSetModeView, RuntimeStatusView, RuntimeTransitionListView

urlpatterns = [
    path('status/', RuntimeStatusView.as_view(), name='status'),
    path('modes/', RuntimeModesView.as_view(), name='modes'),
    path('set-mode/', RuntimeSetModeView.as_view(), name='set_mode'),
    path('transitions/', RuntimeTransitionListView.as_view(), name='transitions'),
    path('capabilities/', RuntimeCapabilitiesView.as_view(), name='capabilities'),
]
