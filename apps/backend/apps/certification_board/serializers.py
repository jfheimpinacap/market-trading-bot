from rest_framework import serializers

from apps.certification_board.models import (
    CertificationDecisionLog,
    CertificationEvidenceSnapshot,
    CertificationRun,
    OperatingEnvelope,
)


class CertificationEvidenceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationEvidenceSnapshot
        fields = '__all__'


class OperatingEnvelopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingEnvelope
        fields = '__all__'


class CertificationDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationDecisionLog
        fields = '__all__'


class CertificationRunSerializer(serializers.ModelSerializer):
    evidence_snapshot = CertificationEvidenceSnapshotSerializer(read_only=True)
    operating_envelope = OperatingEnvelopeSerializer(read_only=True)
    decision_logs = CertificationDecisionLogSerializer(read_only=True, many=True)

    class Meta:
        model = CertificationRun
        fields = '__all__'


class RunCertificationReviewRequestSerializer(serializers.Serializer):
    decision_mode = serializers.ChoiceField(choices=['RECOMMENDATION_ONLY', 'MANUAL_APPLY'], default='RECOMMENDATION_ONLY', required=False)
    metadata = serializers.DictField(required=False)


class ApplyCertificationDecisionRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    apply_safe_state = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
