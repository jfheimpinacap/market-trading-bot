from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notification_center.models import NotificationChannel, NotificationDelivery, NotificationRule
from apps.notification_center.serializers import (
    NotificationChannelSerializer,
    NotificationDeliverySerializer,
    NotificationRuleSerializer,
    TriggerSendSerializer,
)
from apps.notification_center.services import get_notification_summary, send_alert_notifications, send_digest_notifications
from apps.notification_center.services.channels import ensure_default_ui_channel
from apps.operator_alerts.models import OperatorAlert, OperatorDigest


class NotificationChannelListCreateView(generics.ListCreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NotificationChannelSerializer

    def get_queryset(self):
        ensure_default_ui_channel()
        return NotificationChannel.objects.order_by('name', 'id')


class NotificationRuleListCreateView(generics.ListCreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NotificationRuleSerializer

    def get_queryset(self):
        return NotificationRule.objects.order_by('name', 'id')


class NotificationDeliveryListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NotificationDeliverySerializer

    def get_queryset(self):
        queryset = NotificationDelivery.objects.select_related('channel', 'related_alert', 'related_digest').order_by('-created_at', '-id')
        status_filter = self.request.query_params.get('status')
        mode_filter = self.request.query_params.get('mode')
        if status_filter:
            queryset = queryset.filter(delivery_status=status_filter.upper())
        if mode_filter:
            queryset = queryset.filter(delivery_mode=mode_filter)
        return queryset[:200]


class NotificationDeliveryDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = NotificationDeliverySerializer
    queryset = NotificationDelivery.objects.select_related('channel', 'related_alert', 'related_digest').order_by('-created_at', '-id')


class SendAlertNotificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, alert_id, *args, **kwargs):
        serializer = TriggerSendSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        alert = get_object_or_404(OperatorAlert, pk=alert_id)
        deliveries = send_alert_notifications(alert, force=serializer.validated_data['force'])
        return Response(NotificationDeliverySerializer(deliveries, many=True).data, status=status.HTTP_200_OK)


class SendDigestNotificationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, digest_id, *args, **kwargs):
        serializer = TriggerSendSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        digest = get_object_or_404(OperatorDigest, pk=digest_id)
        deliveries = send_digest_notifications(digest, force=serializer.validated_data['force'])
        return Response(NotificationDeliverySerializer(deliveries, many=True).data, status=status.HTTP_200_OK)


class NotificationSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ensure_default_ui_channel()
        return Response(get_notification_summary(), status=status.HTTP_200_OK)
