from django.urls import include, path

urlpatterns = [
    path('health/', include(('apps.health.urls', 'health'), namespace='health')),
    path('markets/', include(('apps.markets.urls', 'markets'), namespace='markets')),
    path('paper/', include(('apps.paper_trading.urls', 'paper_trading'), namespace='paper_trading')),
    path('signals/', include(('apps.signals.urls', 'signals'), namespace='signals')),
    path('agents/', include(('apps.agents.urls', 'agents'), namespace='agents')),
    path('audit/', include(('apps.audit.urls', 'audit'), namespace='audit')),
]
