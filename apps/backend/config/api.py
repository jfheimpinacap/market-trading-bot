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
    path('proposals/', include(('apps.proposal_engine.urls', 'proposal_engine'), namespace='proposal_engine')),
    path('semi-auto/', include(('apps.semi_auto_demo.urls', 'semi_auto_demo'), namespace='semi_auto_demo')),
    path('continuous-demo/', include(('apps.continuous_demo.urls', 'continuous_demo'), namespace='continuous_demo')),
    path('safety/', include(('apps.safety_guard.urls', 'safety_guard'), namespace='safety_guard')),
    path('evaluation/', include(('apps.evaluation_lab.urls', 'evaluation_lab'), namespace='evaluation_lab')),
    path('learning/', include(('apps.learning_memory.urls', 'learning_memory'), namespace='learning_memory')),
    path('real-sync/', include(('apps.real_data_sync.urls', 'real_data_sync'), namespace='real_data_sync')),
    path('real-ops/', include(('apps.real_market_ops.urls', 'real_market_ops'), namespace='real_market_ops')),
]
