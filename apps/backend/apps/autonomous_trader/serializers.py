from rest_framework import serializers

from apps.autonomous_trader.models import (
    AutonomousDispatchRecord,
    AutonomousExecutionDecision,
    AutonomousExecutionIntakeCandidate,
    AutonomousExecutionIntakeRun,
    AutonomousExecutionRecommendation,
    AutonomousFeedbackCandidateContext,
    AutonomousFeedbackInfluenceRecord,
    AutonomousFeedbackRecommendation,
    AutonomousFeedbackReuseRun,
    AutonomousLearningHandoff,
    AutonomousOutcomeHandoffRecommendation,
    AutonomousOutcomeHandoffRun,
    AutonomousPostmortemHandoff,
    AutonomousSizingContext,
    AutonomousSizingDecision,
    AutonomousSizingRecommendation,
    AutonomousSizingRun,
    AutonomousPositionActionDecision,
    AutonomousPositionActionExecution,
    AutonomousPositionWatchCandidate,
    AutonomousPositionWatchRecommendation,
    AutonomousPositionWatchRun,
    AutonomousTradeCandidate,
    AutonomousTradeCycleRun,
    AutonomousTradeDecision,
    AutonomousTradeExecution,
    AutonomousTradeOutcome,
    AutonomousTradeWatchRecord,
)


class RunCycleSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    cycle_mode = serializers.CharField(required=False, default='FULL_AUTONOMOUS_PAPER_LOOP')
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100, default=25)


class RunOutcomeHandoffSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=500, default=100)


class RunFeedbackReuseSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    cycle_run_id = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=25)


class RunSizingSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    cycle_run_id = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=25)


class RunPositionWatchSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=50)


class RunExecutionIntakeSerializer(serializers.Serializer):
    actor = serializers.CharField(required=False, default='operator-ui', allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200, default=25)


class AutonomousTradeCycleRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousTradeCycleRun
        fields = '__all__'


class AutonomousTradeCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeCandidate
        fields = '__all__'


class AutonomousTradeDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeDecision
        fields = '__all__'


class AutonomousTradeExecutionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeExecution
        fields = '__all__'


class AutonomousTradeWatchRecordSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_execution.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeWatchRecord
        fields = '__all__'


class AutonomousTradeOutcomeSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_execution.linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousTradeOutcome
        fields = '__all__'


class AutonomousExecutionIntakeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousExecutionIntakeRun
        fields = '__all__'


class AutonomousExecutionIntakeCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousExecutionIntakeCandidate
        fields = '__all__'


class AutonomousExecutionDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_intake_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousExecutionDecision
        fields = '__all__'


class AutonomousDispatchRecordSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_execution_decision.linked_intake_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousDispatchRecord
        fields = '__all__'


class AutonomousExecutionRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_market.title', read_only=True)

    class Meta:
        model = AutonomousExecutionRecommendation
        fields = '__all__'


class AutonomousOutcomeHandoffRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousOutcomeHandoffRun
        fields = '__all__'


class AutonomousPostmortemHandoffSerializer(serializers.ModelSerializer):
    outcome_type = serializers.CharField(source='linked_outcome.outcome_type', read_only=True)

    class Meta:
        model = AutonomousPostmortemHandoff
        fields = '__all__'


class AutonomousLearningHandoffSerializer(serializers.ModelSerializer):
    outcome_type = serializers.CharField(source='linked_outcome.outcome_type', read_only=True)

    class Meta:
        model = AutonomousLearningHandoff
        fields = '__all__'


class AutonomousOutcomeHandoffRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousOutcomeHandoffRecommendation
        fields = '__all__'


class AutonomousFeedbackReuseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousFeedbackReuseRun
        fields = '__all__'


class AutonomousFeedbackCandidateContextSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousFeedbackCandidateContext
        fields = '__all__'


class AutonomousFeedbackInfluenceRecordSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousFeedbackInfluenceRecord
        fields = '__all__'


class AutonomousFeedbackRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousFeedbackRecommendation
        fields = '__all__'


class AutonomousSizingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSizingRun
        fields = '__all__'


class AutonomousSizingContextSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousSizingContext
        fields = '__all__'


class AutonomousSizingDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousSizingDecision
        fields = '__all__'


class AutonomousSizingRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousSizingRecommendation
        fields = '__all__'


class AutonomousPositionWatchRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousPositionWatchRun
        fields = '__all__'


class AutonomousPositionWatchCandidateSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_market.title', read_only=True)

    class Meta:
        model = AutonomousPositionWatchCandidate
        fields = '__all__'


class AutonomousPositionActionDecisionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_watch_candidate.linked_market.title', read_only=True)

    class Meta:
        model = AutonomousPositionActionDecision
        fields = '__all__'


class AutonomousPositionActionExecutionSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='linked_position.market.title', read_only=True)

    class Meta:
        model = AutonomousPositionActionExecution
        fields = '__all__'


class AutonomousPositionWatchRecommendationSerializer(serializers.ModelSerializer):
    market_title = serializers.CharField(source='target_position.market.title', read_only=True)

    class Meta:
        model = AutonomousPositionWatchRecommendation
        fields = '__all__'
