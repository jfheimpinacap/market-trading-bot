from rest_framework import serializers

from apps.trace_explorer.models import TraceEdge, TraceNode, TraceQueryRun, TraceRoot


class TraceNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TraceNode
        fields = '__all__'


class TraceEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TraceEdge
        fields = '__all__'


class TraceRootSerializer(serializers.ModelSerializer):
    class Meta:
        model = TraceRoot
        fields = '__all__'


class TraceQueryRunSerializer(serializers.ModelSerializer):
    root_type = serializers.CharField(source='root.root_type', read_only=True)
    root_object_id = serializers.CharField(source='root.root_object_id', read_only=True)

    class Meta:
        model = TraceQueryRun
        fields = '__all__'


class TraceQueryRequestSerializer(serializers.Serializer):
    root_type = serializers.CharField()
    root_id = serializers.CharField()


class TraceQueryResponseSerializer(serializers.Serializer):
    root = TraceRootSerializer()
    nodes = TraceNodeSerializer(many=True)
    edges = TraceEdgeSerializer(many=True)
    snapshot = serializers.DictField()
    partial = serializers.BooleanField()
    query_run = TraceQueryRunSerializer()
