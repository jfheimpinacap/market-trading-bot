from django.db.models import Count
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trace_explorer.models import TraceQueryRun, TraceRoot
from apps.trace_explorer.serializers import TraceQueryRequestSerializer, TraceQueryResponseSerializer, TraceQueryRunSerializer, TraceRootSerializer
from apps.trace_explorer.services.provenance import build_provenance_snapshot
from apps.trace_explorer.services.query import run_trace_query
from apps.trace_explorer.services.roots import resolve_root


class TraceQueryView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = TraceQueryRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = run_trace_query(
            root_type=serializer.validated_data['root_type'],
            root_id=str(serializer.validated_data['root_id']),
            query_type='api_query',
            query_payload=serializer.validated_data,
        )
        return Response(TraceQueryResponseSerializer(result).data, status=status.HTTP_200_OK)


class TraceRootListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TraceRootSerializer
    queryset = TraceRoot.objects.order_by('-updated_at', '-id')[:200]


class TraceRootDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TraceRootSerializer
    queryset = TraceRoot.objects.order_by('-updated_at', '-id')


class TraceSnapshotView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, root_type: str, root_id: str, *args, **kwargs):
        resolved = resolve_root(root_type=root_type, root_id=root_id)
        nodes = list(resolved.root.nodes.order_by('happened_at', 'id'))
        edges = list(resolved.root.edges.select_related('from_node', 'to_node').order_by('id'))
        if not nodes:
            result = run_trace_query(root_type=root_type, root_id=root_id, query_type='snapshot_on_demand')
            return Response({'snapshot': result['snapshot'], 'partial': result['partial']}, status=status.HTTP_200_OK)
        snapshot = build_provenance_snapshot(resolved.root, nodes, edges)
        return Response({'snapshot': snapshot, 'partial': len(nodes) < 4}, status=status.HTTP_200_OK)


class TraceQueryRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = TraceQueryRunSerializer
    queryset = TraceQueryRun.objects.select_related('root').order_by('-created_at', '-id')[:200]


class TraceSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        by_type = list(
            TraceRoot.objects.values('root_type').annotate(count=Count('id')).order_by('root_type')
        )
        latest_query = TraceQueryRun.objects.select_related('root').order_by('-created_at', '-id').first()
        return Response(
            {
                'total_roots': TraceRoot.objects.count(),
                'total_nodes': sum(root.nodes.count() for root in TraceRoot.objects.all()[:200]),
                'total_edges': sum(root.edges.count() for root in TraceRoot.objects.all()[:200]),
                'roots_by_type': by_type,
                'latest_query_run': TraceQueryRunSerializer(latest_query).data if latest_query else None,
            },
            status=status.HTTP_200_OK,
        )
