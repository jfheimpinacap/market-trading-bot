from django.contrib import admin

from apps.venue_account.models import (
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
    VenueReconciliationIssue,
    VenueReconciliationRun,
)


admin.site.register(VenueAccountSnapshot)
admin.site.register(VenueBalanceSnapshot)
admin.site.register(VenuePositionSnapshot)
admin.site.register(VenueOrderSnapshot)
admin.site.register(VenueReconciliationRun)
admin.site.register(VenueReconciliationIssue)
