from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.broker_bridge.models import BrokerOrderIntent
from apps.broker_bridge.serializers import ActionMetadataRequestSerializer, BrokerOrderIntentSerializer, CreateIntentRequestSerializer
from apps.broker_bridge.services import create_intent, get_readiness_summary, run_dry_run, validate_intent


class BrokerIntentCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = CreateIntentRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        try:
            intent = create_intent(
                source_type=serializer.validated_data.get('source_type', 'paper_order'),
                source_id=serializer.validated_data.get('source_id'),
                payload=serializer.validated_data.get('payload') or {},
            )
        except (ValidationError, BrokerOrderIntent.DoesNotExist) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'intent': BrokerOrderIntentSerializer(intent).data}, status=status.HTTP_201_CREATED)


class BrokerIntentValidateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = ActionMetadataRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        intent = BrokerOrderIntent.objects.select_related('market').get(pk=pk)
        validation = validate_intent(intent=intent, metadata=serializer.validated_data.get('metadata') or {})
        return Response({'intent': BrokerOrderIntentSerializer(intent).data, 'validation': validation.id}, status=status.HTTP_200_OK)


class BrokerIntentDryRunView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, pk: int, *args, **kwargs):
        serializer = ActionMetadataRequestSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        intent = BrokerOrderIntent.objects.select_related('market').get(pk=pk)
        dry_run = run_dry_run(intent=intent, metadata=serializer.validated_data.get('metadata') or {})
        return Response({'intent': BrokerOrderIntentSerializer(intent).data, 'dry_run': dry_run.id}, status=status.HTTP_200_OK)


class BrokerIntentListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BrokerOrderIntentSerializer

    def get_queryset(self):
        return BrokerOrderIntent.objects.select_related('market', 'related_paper_order').prefetch_related('validations', 'dry_runs').order_by('-created_at', '-id')[:100]


class BrokerIntentDetailView(generics.RetrieveAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BrokerOrderIntentSerializer
    queryset = BrokerOrderIntent.objects.select_related('market', 'related_paper_order').prefetch_related('validations', 'dry_runs').order_by('-created_at', '-id')


class BrokerBridgeSummaryView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_readiness_summary(), status=status.HTTP_200_OK)
