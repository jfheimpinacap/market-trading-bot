from django.contrib import admin

from apps.semi_auto_demo.models import PendingApproval, SemiAutoRun

admin.site.register(SemiAutoRun)
admin.site.register(PendingApproval)
