from django.db.models import Count, Max
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.memory_retrieval.models import MemoryDocument, MemoryRetrievalRun
from apps.memory_retrieval.serializers import (
    MemoryDocumentSerializer,
    MemoryIndexRequestSerializer,
    MemoryRetrievalRunSerializer,
    MemoryRetrieveRequestSerializer,
    MemorySummarySerializer,
    MemoryPrecedentSummarySerializer,
    serialize_run_with_summary,
)
from apps.memory_retrieval.services import build_precedent_summary, retrieve_precedents, run_indexing


class MemoryIndexView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = MemoryIndexRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = run_indexing(
            sources=serializer.validated_data.get('sources'),
            force_reembed=serializer.validated_data.get('force_reembed', False),
        )
        return Response(payload, status=status.HTTP_200_OK)


class MemoryRetrieveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = MemoryRetrieveRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        run = retrieve_precedents(**serializer.validated_data)
        return Response(serialize_run_with_summary(run), status=status.HTTP_200_OK)


class MemoryDocumentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MemoryDocumentSerializer

    def get_queryset(self):
        queryset = MemoryDocument.objects.order_by('-created_at', '-id')
        doc_type = self.request.query_params.get('document_type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        return queryset[:300]


class MemoryRetrievalRunListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MemoryRetrievalRunSerializer

    def get_queryset(self):
        return MemoryRetrievalRun.objects.prefetch_related('precedents__memory_document').order_by('-created_at', '-id')[:100]


class MemoryRetrievalRunDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = MemoryRetrievalRunSerializer

    def get_queryset(self):
        return MemoryRetrievalRun.objects.prefetch_related('precedents__memory_document').order_by('-created_at', '-id')


class MemorySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        docs = MemoryDocument.objects.all()
        by_type = {item['document_type']: item['total'] for item in docs.values('document_type').annotate(total=Count('id'))}
        by_source = {item['source_app']: item['total'] for item in docs.values('source_app').annotate(total=Count('id'))}
        latest_run = MemoryRetrievalRun.objects.prefetch_related('precedents__memory_document').order_by('-created_at', '-id').first()
        payload = {
            'documents_indexed': docs.count(),
            'retrieval_runs': MemoryRetrievalRun.objects.count(),
            'document_types': by_type,
            'source_apps': by_source,
            'last_indexed_document_at': docs.aggregate(last=Max('updated_at')).get('last'),
            'last_retrieval_run': latest_run,
        }
        return Response(MemorySummarySerializer(payload).data, status=status.HTTP_200_OK)


class MemoryPrecedentSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        run_id = request.query_params.get('run_id')
        run = None
        if run_id:
            run = MemoryRetrievalRun.objects.filter(id=run_id).prefetch_related('precedents__memory_document').first()
        if run is None:
            run = MemoryRetrievalRun.objects.prefetch_related('precedents__memory_document').order_by('-created_at', '-id').first()
        if run is None:
            return Response({'detail': 'No retrieval runs available yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(MemoryPrecedentSummarySerializer(build_precedent_summary(run)).data, status=status.HTTP_200_OK)
