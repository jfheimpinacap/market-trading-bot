from django.contrib import admin

from apps.execution_venue.models import VenueCapabilityProfile, VenueOrderPayload, VenueOrderResponse, VenueParityRun

admin.site.register(VenueCapabilityProfile)
admin.site.register(VenueOrderPayload)
admin.site.register(VenueOrderResponse)
admin.site.register(VenueParityRun)
