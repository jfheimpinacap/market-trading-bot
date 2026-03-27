from rest_framework import serializers

from apps.runbook_engine.models import RunbookActionResult, RunbookInstance, RunbookStep, RunbookTemplate


class RunbookTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunbookTemplate
        fields = '__all__'


class RunbookActionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunbookActionResult
        fields = '__all__'


class RunbookStepSerializer(serializers.ModelSerializer):
    action_results = RunbookActionResultSerializer(many=True, read_only=True)

    class Meta:
        model = RunbookStep
        fields = '__all__'


class RunbookInstanceSerializer(serializers.ModelSerializer):
    template = RunbookTemplateSerializer(read_only=True)
    steps = RunbookStepSerializer(many=True, read_only=True)

    class Meta:
        model = RunbookInstance
        fields = '__all__'


class RunbookCreateSerializer(serializers.Serializer):
    template_slug = serializers.CharField(max_length=120)
    source_object_type = serializers.CharField(max_length=80)
    source_object_id = serializers.CharField(max_length=80)
    priority = serializers.ChoiceField(choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], default='MEDIUM')
    summary = serializers.CharField(required=False, allow_blank=True, max_length=255)
    metadata = serializers.JSONField(required=False)


class RunbookCompleteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
