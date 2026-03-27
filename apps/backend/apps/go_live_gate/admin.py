from django.contrib import admin

from apps.go_live_gate.models import CapitalFirewallRule, GoLiveApprovalRequest, GoLiveChecklistRun, GoLiveRehearsalRun

admin.site.register(CapitalFirewallRule)
admin.site.register(GoLiveChecklistRun)
admin.site.register(GoLiveApprovalRequest)
admin.site.register(GoLiveRehearsalRun)
