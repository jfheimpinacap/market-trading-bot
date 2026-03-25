from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.runtime_governor.models import RuntimeTransitionLog
from apps.runtime_governor.serializers import RuntimeSetModeSerializer, RuntimeTransitionLogSerializer
from apps.runtime_governor.services import (
    get_capabilities_for_current_mode,
    get_runtime_status,
    list_modes_with_constraints,
    set_runtime_mode,
)


class RuntimeStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        snapshot = get_runtime_status()
        payload = {
            'state': {
                'id': snapshot['state'].id,
                'current_mode': snapshot['state'].current_mode,
                'desired_mode': snapshot['state'].desired_mode,
                'status': snapshot['state'].status,
                'set_by': snapshot['state'].set_by,
                'rationale': snapshot['state'].rationale,
                'effective_at': snapshot['state'].effective_at,
                'updated_at': snapshot['state'].updated_at,
                'metadata': snapshot['state'].metadata,
            },
            'readiness_status': snapshot['readiness_status'],
            'safety_status': snapshot['safety_status'],
            'constraints': snapshot['constraints'],
        }
        return Response(payload, status=status.HTTP_200_OK)


class RuntimeModesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(list_modes_with_constraints(), status=status.HTTP_200_OK)


class RuntimeSetModeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = RuntimeSetModeSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = set_runtime_mode(
            requested_mode=serializer.validated_data['mode'],
            set_by=serializer.validated_data.get('set_by', 'operator') or 'operator',
            rationale=serializer.validated_data.get('rationale', ''),
            metadata=serializer.validated_data.get('metadata', {}),
        )

        if not result['decision'].allowed:
            return Response(
                {
                    'changed': False,
                    'state': {
                        'current_mode': result['state'].current_mode,
                        'status': result['state'].status,
                    },
                    'blocked_reasons': result['decision'].reasons,
                    'message': 'This mode is currently blocked by readiness or safety constraints.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                'changed': result['changed'],
                'state': {
                    'current_mode': result['state'].current_mode,
                    'status': result['state'].status,
                    'set_by': result['state'].set_by,
                    'rationale': result['state'].rationale,
                    'effective_at': result['state'].effective_at,
                },
                'reasons': result['decision'].reasons,
            },
            status=status.HTTP_200_OK,
        )


class RuntimeTransitionListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = RuntimeTransitionLogSerializer

    def get_queryset(self):
        return RuntimeTransitionLog.objects.order_by('-created_at', '-id')[:100]


class RuntimeCapabilitiesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(get_capabilities_for_current_mode(), status=status.HTTP_200_OK)
