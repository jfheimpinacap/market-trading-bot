from django.contrib import admin

from apps.trace_explorer.models import TraceEdge, TraceNode, TraceQueryRun, TraceRoot

admin.site.register(TraceRoot)
admin.site.register(TraceNode)
admin.site.register(TraceEdge)
admin.site.register(TraceQueryRun)
