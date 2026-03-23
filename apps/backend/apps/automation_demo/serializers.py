from rest_framework import serializers

from apps.automation_demo.models import DemoAutomationRun


class DemoAutomationRunSerializer(serializers.ModelSerializer):
    step_results = serializers.SerializerMethodField()

    class Meta:
        model = DemoAutomationRun
        fields = (
            'id',
            'action_type',
            'status',
            'summary',
            'details',
            'step_results',
            'triggered_from',
            'started_at',
            'finished_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def get_step_results(self, obj):
        details = obj.details or {}
        return details.get('steps', [])


class DemoAutomationActionRequestSerializer(serializers.Serializer):
    triggered_from = serializers.ChoiceField(
        choices=DemoAutomationRun.TriggeredFrom.choices,
        required=False,
        default=DemoAutomationRun.TriggeredFrom.API,
    )


class DemoAutomationSummarySerializer(serializers.Serializer):
    recent_runs_count = serializers.IntegerField()
    available_actions = serializers.ListField(child=serializers.DictField())
    latest_run = serializers.JSONField(allow_null=True)
    last_by_action = serializers.JSONField()
