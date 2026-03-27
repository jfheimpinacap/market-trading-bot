from django.contrib import admin

from apps.certification_board.models import (
    CertificationDecisionLog,
    CertificationEvidenceSnapshot,
    CertificationRun,
    OperatingEnvelope,
)

admin.site.register(CertificationEvidenceSnapshot)
admin.site.register(OperatingEnvelope)
admin.site.register(CertificationRun)
admin.site.register(CertificationDecisionLog)
