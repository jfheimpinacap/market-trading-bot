from django.contrib import admin

from apps.chaos_lab.models import ChaosExperiment, ChaosObservation, ChaosRun, ResilienceBenchmark

admin.site.register(ChaosExperiment)
admin.site.register(ChaosRun)
admin.site.register(ChaosObservation)
admin.site.register(ResilienceBenchmark)
