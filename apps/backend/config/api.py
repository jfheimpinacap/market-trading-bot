from django.urls import include, path

urlpatterns = [
    path('health/', include(('apps.health.urls', 'health'), namespace='health')),
    path('markets/', include(('apps.markets.urls', 'markets'), namespace='markets')),
    path('paper/', include(('apps.paper_trading.urls', 'paper_trading'), namespace='paper_trading')),
    path('risk/', include(('apps.risk_demo.urls', 'risk_demo'), namespace='risk_demo')),
    path('signals/', include(('apps.signals.urls', 'signals'), namespace='signals')),
    path('reviews/', include(('apps.postmortem_demo.urls', 'postmortem_demo'), namespace='postmortem_demo')),
    path('agents/', include(('apps.agents.urls', 'agents'), namespace='agents')),
    path('audit/', include(('apps.audit.urls', 'audit'), namespace='audit')),
    path('automation/', include(('apps.automation_demo.urls', 'automation_demo'), namespace='automation_demo')),
    path('policy/', include(('apps.policy_engine.urls', 'policy_engine'), namespace='policy_engine')),
]
