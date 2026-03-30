from rest_framework import serializers

from apps.certification_board.models import (
    BaselineResponseLifecycleRun,
    BaselineResponseActionRun,
    DownstreamAcknowledgement,
    DownstreamAcknowledgementStatus,
    DownstreamLifecycleOutcome,
    DownstreamLifecycleOutcomeStatus,
    DownstreamLifecycleOutcomeType,
    ResponseLifecycleRecommendation,
    ResponseLifecycleRecommendationType,
    ResponseReviewStageRecord,
    ResponseReviewStageStatus,
    ResponseReviewStageType,
    ResponseActionCandidate,
    ResponseActionRecommendation,
    ResponseCaseTrackingRecord,
    ResponseRoutingAction,
    ResponseRoutingActionType,
    ResponseCaseDownstreamStatus,
    BaselineResponseCase,
    BaselineResponseRecommendation,
    BaselineResponseRun,
    ResponseEvidencePack,
    ResponseRoutingDecision,
    BaselineHealthCandidate,
    BaselineHealthRecommendation,
    BaselineHealthRun,
    BaselineHealthSignal,
    BaselineHealthStatus,
    ActivePaperBindingRecord,
    BaselineActivationCandidate,
    BaselineActivationRecommendation,
    BaselineActivationRun,
    BaselineBindingSnapshot,
    BaselineConfirmationCandidate,
    BaselineConfirmationRecommendation,
    BaselineConfirmationRun,
    CertificationCandidate,
    CertificationDecision,
    CertificationDecisionLog,
    CertificationEvidencePack,
    CertificationEvidenceSnapshot,
    CertificationRecommendation,
    CertificationRun,
    RolloutCertificationRun,
    OperatingEnvelope,
    PaperBaselineActivation,
    PaperBaselineConfirmation,
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


class RolloutCertificationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutCertificationRun
        fields = '__all__'


class CertificationCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationCandidate
        fields = '__all__'


class CertificationEvidencePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationEvidencePack
        fields = '__all__'


class CertificationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationDecision
        fields = '__all__'


class CertificationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificationRecommendation
        fields = '__all__'


class RunPostRolloutReviewRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    rollout_execution_run_id = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.DictField(required=False)


class RunBaselineConfirmationReviewRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class ConfirmPaperBaselineRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    rationale = serializers.CharField(required=False, allow_blank=True, default='')


class BaselineConfirmationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineConfirmationRun
        fields = '__all__'


class BaselineConfirmationCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineConfirmationCandidate
        fields = '__all__'


class PaperBaselineConfirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperBaselineConfirmation
        fields = '__all__'


class BaselineBindingSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineBindingSnapshot
        fields = '__all__'


class BaselineConfirmationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineConfirmationRecommendation
        fields = '__all__'


class RunBaselineActivationReviewRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class ActivatePaperBaselineRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    rationale = serializers.CharField(required=False, allow_blank=True, default='')


class RollbackBaselineActivationRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')


class BaselineActivationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineActivationRun
        fields = '__all__'


class BaselineActivationCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineActivationCandidate
        fields = '__all__'


class PaperBaselineActivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperBaselineActivation
        fields = '__all__'


class ActivePaperBindingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivePaperBindingRecord
        fields = '__all__'


class BaselineActivationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineActivationRecommendation
        fields = '__all__'


class RunBaselineHealthReviewRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class BaselineHealthRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineHealthRun
        fields = '__all__'


class BaselineHealthCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineHealthCandidate
        fields = '__all__'


class BaselineHealthStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineHealthStatus
        fields = '__all__'


class BaselineHealthSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineHealthSignal
        fields = '__all__'


class BaselineHealthRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineHealthRecommendation
        fields = '__all__'


class RunBaselineResponseReviewRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class BaselineResponseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineResponseRun
        fields = '__all__'


class BaselineResponseCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineResponseCase
        fields = '__all__'


class ResponseEvidencePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseEvidencePack
        fields = '__all__'


class ResponseRoutingDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseRoutingDecision
        fields = '__all__'


class BaselineResponseRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineResponseRecommendation
        fields = '__all__'


class RunBaselineResponseActionsRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class RunBaselineResponseLifecycleRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class BaselineResponseActionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineResponseActionRun
        fields = '__all__'


class ResponseActionCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseActionCandidate
        fields = '__all__'


class ResponseRoutingActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseRoutingAction
        fields = '__all__'


class ResponseCaseTrackingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseCaseTrackingRecord
        fields = '__all__'


class ResponseActionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseActionRecommendation
        fields = '__all__'


class BaselineResponseLifecycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineResponseLifecycleRun
        fields = '__all__'


class DownstreamAcknowledgementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownstreamAcknowledgement
        fields = '__all__'


class ResponseReviewStageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseReviewStageRecord
        fields = '__all__'


class DownstreamLifecycleOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownstreamLifecycleOutcome
        fields = '__all__'


class ResponseLifecycleRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseLifecycleRecommendation
        fields = '__all__'


class AcknowledgeResponseCaseRequestSerializer(serializers.Serializer):
    acknowledgement_status = serializers.ChoiceField(
        choices=DownstreamAcknowledgementStatus.choices,
        required=False,
        default=DownstreamAcknowledgementStatus.ACKNOWLEDGED,
    )
    acknowledged_by = serializers.CharField(required=False, default='operator-ui')
    acknowledgement_notes = serializers.CharField(required=False, allow_blank=True, default='')
    linked_target_reference = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)


class UpdateResponseStageRequestSerializer(serializers.Serializer):
    stage_type = serializers.ChoiceField(choices=ResponseReviewStageType.choices)
    stage_status = serializers.ChoiceField(choices=ResponseReviewStageStatus.choices)
    stage_notes = serializers.CharField(required=False, allow_blank=True, default='')
    stage_actor = serializers.CharField(required=False, default='operator-ui')
    metadata = serializers.DictField(required=False)


class RecordDownstreamOutcomeRequestSerializer(serializers.Serializer):
    outcome_type = serializers.ChoiceField(choices=DownstreamLifecycleOutcomeType.choices)
    outcome_status = serializers.ChoiceField(choices=DownstreamLifecycleOutcomeStatus.choices)
    outcome_rationale = serializers.CharField(required=False, allow_blank=True, default='')
    linked_target_reference = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)


class RouteResponseCaseRequestSerializer(serializers.Serializer):
    action_type = serializers.ChoiceField(
        choices=ResponseRoutingActionType.choices,
        required=False,
    )
    routing_target = serializers.CharField(required=False, allow_blank=True)
    rationale = serializers.CharField(required=False, allow_blank=True, default='')
    reason_codes = serializers.ListField(child=serializers.CharField(), required=False)
    routed_by = serializers.CharField(required=False, default='operator-ui')
    linked_target_artifact = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)


class UpdateResponseTrackingRequestSerializer(serializers.Serializer):
    downstream_status = serializers.ChoiceField(choices=ResponseCaseDownstreamStatus.choices)
    tracking_notes = serializers.CharField(required=False, allow_blank=True, default='')
    tracked_by = serializers.CharField(required=False, default='operator-ui')
    linked_downstream_reference = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)


class CloseResponseCaseRequestSerializer(serializers.Serializer):
    tracked_by = serializers.CharField(required=False, default='operator-ui')
    tracking_notes = serializers.CharField(required=False, allow_blank=True, default='')
    linked_downstream_reference = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)
