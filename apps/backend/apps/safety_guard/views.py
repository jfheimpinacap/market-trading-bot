from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.safety_guard.models import SafetyEvent
from apps.safety_guard.serializers import SafetyEventSerializer, SafetyPolicyConfigSerializer
from apps.safety_guard.services import disable_kill_switch, enable_kill_switch, get_safety_status
from apps.safety_guard.services.cooldown import clear_cooldown
from apps.safety_guard.services.kill_switch import get_or_create_config


class SafetyStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_safety_status(), status=status.HTTP_200_OK)


class SafetyEventListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SafetyEventSerializer

    def get_queryset(self):
        return SafetyEvent.objects.order_by('-created_at', '-id')[:100]


class SafetyEventDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SafetyEventSerializer
    queryset = SafetyEvent.objects.order_by('-created_at', '-id')


class SafetyKillSwitchEnableView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        config = enable_kill_switch()
        return Response({'kill_switch_enabled': config.kill_switch_enabled, 'status': config.status}, status=status.HTTP_200_OK)


class SafetyKillSwitchDisableView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        config = disable_kill_switch()
        return Response({'kill_switch_enabled': config.kill_switch_enabled, 'status': config.status}, status=status.HTTP_200_OK)


class SafetyConfigView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(SafetyPolicyConfigSerializer(get_or_create_config()).data)

    def post(self, request, *args, **kwargs):
        config = get_or_create_config()
        serializer = SafetyPolicyConfigSerializer(config, data=request.data or {}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SafetyResetCooldownView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        config = clear_cooldown()
        return Response({'status': config.status, 'cooldown_until_cycle': config.cooldown_until_cycle}, status=status.HTTP_200_OK)


class SafetySummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        status_snapshot = get_safety_status()
        recent = SafetyEventSerializer(SafetyEvent.objects.order_by('-created_at', '-id')[:10], many=True).data
        return Response({'status': status_snapshot, 'recent_events': recent}, status=status.HTTP_200_OK)
