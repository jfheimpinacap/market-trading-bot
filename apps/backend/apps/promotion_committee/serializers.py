from rest_framework import serializers

from apps.champion_challenger.serializers import StackProfileBindingSerializer
from apps.promotion_committee.models import (
    AdoptionActionCandidate,
    AdoptionActionRecommendation,
    AdoptionRollbackPlan,
    ManualRollbackExecution,
    CheckpointOutcomeRecord,
    PostRolloutStatus,
    RolloutExecutionRecommendation,
    RolloutExecutionRecord,
    RolloutExecutionRun,
    ManualRolloutPlan,
    ManualAdoptionAction,
    PromotionCase,
    PromotionAdoptionRun,
    PromotionDecisionLog,
    PromotionDecisionRecommendation,
    PromotionEvidencePack,
    RolloutActionCandidate,
    RolloutCheckpointPlan,
    RolloutPreparationRecommendation,
    RolloutPreparationRun,
    PromotionReviewCycleRun,
    PromotionReviewRun,
    StackEvidenceSnapshot,
)


class StackEvidenceSnapshotSerializer(serializers.ModelSerializer):
    champion_binding = StackProfileBindingSerializer(read_only=True)
    challenger_binding = StackProfileBindingSerializer(read_only=True)

    class Meta:
        model = StackEvidenceSnapshot
        fields = '__all__'


class PromotionDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionDecisionLog
        fields = '__all__'


class PromotionReviewRunSerializer(serializers.ModelSerializer):
    evidence_snapshot = StackEvidenceSnapshotSerializer(read_only=True)
    decision_logs = PromotionDecisionLogSerializer(read_only=True, many=True)

    class Meta:
        model = PromotionReviewRun
        fields = '__all__'


class PromotionReviewRequestSerializer(serializers.Serializer):
    decision_mode = serializers.ChoiceField(
        choices=['RECOMMENDATION_ONLY', 'MANUAL_APPLY'], default='RECOMMENDATION_ONLY', required=False
    )
    challenger_binding_id = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.DictField(required=False)


class PromotionApplyRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class GovernedPromotionRunRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='promotion_ui')
    linked_experiment_run_id = serializers.IntegerField(required=False, min_value=1)
    metadata = serializers.DictField(required=False)


class PromotionRollbackRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class RolloutExecutionActionSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    rationale = serializers.CharField(required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False)


class CheckpointOutcomeRequestSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator')
    outcome_status = serializers.ChoiceField(choices=['PASSED', 'FAILED', 'WARNING', 'SKIPPED'])
    outcome_rationale = serializers.CharField(required=False, allow_blank=True, default='')
    observed_metrics = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)


class PromotionReviewCycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionReviewCycleRun
        fields = '__all__'


class PromotionCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionCase
        fields = '__all__'


class PromotionEvidencePackSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionEvidencePack
        fields = '__all__'


class PromotionDecisionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionDecisionRecommendation
        fields = '__all__'


class PromotionAdoptionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionAdoptionRun
        fields = '__all__'


class AdoptionActionCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionActionCandidate
        fields = '__all__'


class ManualAdoptionActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualAdoptionAction
        fields = '__all__'


class AdoptionRollbackPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionRollbackPlan
        fields = '__all__'


class AdoptionActionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdoptionActionRecommendation
        fields = '__all__'


class RolloutPreparationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutPreparationRun
        fields = '__all__'


class RolloutActionCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutActionCandidate
        fields = '__all__'


class ManualRolloutPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualRolloutPlan
        fields = '__all__'


class RolloutCheckpointPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutCheckpointPlan
        fields = '__all__'


class ManualRollbackExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualRollbackExecution
        fields = '__all__'


class RolloutPreparationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutPreparationRecommendation
        fields = '__all__'


class RolloutExecutionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutExecutionRun
        fields = '__all__'


class RolloutExecutionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutExecutionRecord
        fields = '__all__'


class CheckpointOutcomeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckpointOutcomeRecord
        fields = '__all__'


class PostRolloutStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostRolloutStatus
        fields = '__all__'


class RolloutExecutionRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolloutExecutionRecommendation
        fields = '__all__'
