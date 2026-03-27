from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.incident_commander.models import IncidentRecord
from apps.incident_commander.serializers import DegradedModeStateSerializer, IncidentRecordSerializer
from apps.incident_commander.services import get_current_degraded_mode_state, mitigate_incident, resolve_incident, run_detection, summarize_incidents


class IncidentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = IncidentRecordSerializer

    def get_queryset(self):
        queryset = IncidentRecord.objects.order_by('-last_seen_at', '-id')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        return queryset[:150]


class IncidentDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = IncidentRecordSerializer
    queryset = IncidentRecord.objects.order_by('-last_seen_at', '-id')


class IncidentCurrentStateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        state = get_current_degraded_mode_state()
        summary = summarize_incidents()
        return Response({'degraded_mode': DegradedModeStateSerializer(state).data, 'summary': summary}, status=status.HTTP_200_OK)


class IncidentRunDetectionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        result = run_detection()
        return Response(result, status=status.HTTP_200_OK)


class IncidentMitigateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        incident = get_object_or_404(IncidentRecord, pk=pk)
        incident = mitigate_incident(incident=incident)
        return Response(IncidentRecordSerializer(incident).data, status=status.HTTP_200_OK)


class IncidentResolveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        incident = get_object_or_404(IncidentRecord, pk=pk)
        incident = resolve_incident(incident=incident, resolution_note=(request.data or {}).get('note', ''))
        return Response(IncidentRecordSerializer(incident).data, status=status.HTTP_200_OK)


class IncidentSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(summarize_incidents(), status=status.HTTP_200_OK)
