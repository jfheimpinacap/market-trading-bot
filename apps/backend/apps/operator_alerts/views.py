from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.operator_alerts.models import OperatorAlert, OperatorDigest
from apps.operator_alerts.serializers import BuildDigestSerializer, OperatorAlertSerializer, OperatorDigestSerializer
from apps.operator_alerts.services import acknowledge_alert, build_digest, get_alerts_summary, rebuild_operator_alerts, resolve_alert


class OperatorAlertListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorAlertSerializer

    def get_queryset(self):
        queryset = OperatorAlert.objects.order_by('-last_seen_at', '-id')
        status_filter = self.request.query_params.get('status')
        severity = self.request.query_params.get('severity')
        source = self.request.query_params.get('source')
        alert_type = self.request.query_params.get('alert_type')

        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        if severity:
            queryset = queryset.filter(severity=severity.lower())
        if source:
            queryset = queryset.filter(source=source)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        return queryset[:150]


class OperatorAlertDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorAlertSerializer
    queryset = OperatorAlert.objects.order_by('-last_seen_at', '-id')


class OperatorAlertSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_alerts_summary(), status=status.HTTP_200_OK)


class OperatorAlertAcknowledgeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        alert = get_object_or_404(OperatorAlert, pk=pk)
        alert = acknowledge_alert(alert)
        return Response(OperatorAlertSerializer(alert).data, status=status.HTTP_200_OK)


class OperatorAlertResolveView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk, *args, **kwargs):
        alert = get_object_or_404(OperatorAlert, pk=pk)
        alert = resolve_alert(alert)
        return Response(OperatorAlertSerializer(alert).data, status=status.HTTP_200_OK)


class OperatorDigestListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorDigestSerializer

    def get_queryset(self):
        return OperatorDigest.objects.order_by('-window_end', '-id')[:60]


class OperatorDigestDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OperatorDigestSerializer
    queryset = OperatorDigest.objects.order_by('-window_end', '-id')


class OperatorBuildDigestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = BuildDigestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        digest = build_digest(**serializer.validated_data)
        return Response(OperatorDigestSerializer(digest).data, status=status.HTTP_201_CREATED)


class OperatorRebuildAlertsView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        result = rebuild_operator_alerts()
        return Response(result, status=status.HTTP_200_OK)
