from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.broker_bridge.models import BrokerOrderIntent
from apps.execution_venue.models import VenueParityRun
from apps.execution_venue.serializers import VenueActionMetadataSerializer, VenueCapabilityProfileSerializer, VenueOrderPayloadSerializer, VenueOrderResponseSerializer, VenueParityRunSerializer
from apps.execution_venue.services import NullSandboxVenueAdapter, build_summary, run_parity


class ExecutionVenueCapabilitiesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        adapter = NullSandboxVenueAdapter()
        return Response(VenueCapabilityProfileSerializer(adapter.get_capabilities()).data, status=status.HTTP_200_OK)


class ExecutionVenueBuildPayloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, intent_id: int, *args, **kwargs):
        serializer = VenueActionMetadataSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            intent = BrokerOrderIntent.objects.select_related('market', 'related_paper_order').get(pk=intent_id)
        except BrokerOrderIntent.DoesNotExist:
            raise ValidationError('Intent not found.')

        adapter = NullSandboxVenueAdapter()
        payload = adapter.build_payload(intent, metadata=serializer.validated_data.get('metadata') or {})
        valid, reason_codes, warnings, missing_fields = adapter.validate_payload(payload)
        return Response(
            {
                'payload': VenueOrderPayloadSerializer(payload).data,
                'validation': {
                    'is_valid': valid,
                    'reason_codes': reason_codes,
                    'warnings': warnings,
                    'missing_fields': missing_fields,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ExecutionVenueDryRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, intent_id: int, *args, **kwargs):
        serializer = VenueActionMetadataSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            intent = BrokerOrderIntent.objects.select_related('market', 'related_paper_order').get(pk=intent_id)
        except BrokerOrderIntent.DoesNotExist:
            raise ValidationError('Intent not found.')

        adapter = NullSandboxVenueAdapter()
        payload = adapter.build_payload(intent, metadata=serializer.validated_data.get('metadata') or {})
        response = adapter.dry_run(payload, metadata=serializer.validated_data.get('metadata') or {})
        return Response(
            {
                'payload': VenueOrderPayloadSerializer(payload).data,
                'response': VenueOrderResponseSerializer(response).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ExecutionVenueRunParityView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, intent_id: int, *args, **kwargs):
        serializer = VenueActionMetadataSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            intent = BrokerOrderIntent.objects.select_related('market', 'related_paper_order').prefetch_related('dry_runs').get(pk=intent_id)
        except BrokerOrderIntent.DoesNotExist:
            raise ValidationError('Intent not found.')

        parity = run_parity(intent, metadata=serializer.validated_data.get('metadata') or {})
        return Response(VenueParityRunSerializer(parity).data, status=status.HTTP_201_CREATED)


class ExecutionVenueParityRunsView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = VenueParityRunSerializer

    def get_queryset(self):
        return VenueParityRun.objects.select_related('intent', 'payload', 'response').order_by('-created_at', '-id')[:100]


class ExecutionVenueSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(build_summary(), status=status.HTTP_200_OK)
