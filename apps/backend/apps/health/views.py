from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import HealthCheckSerializer


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        payload = {
            'status': 'ok',
            'service': 'market-trading-bot-backend',
            'environment': settings.ENVIRONMENT,
            'app_mode': getattr(settings, 'APP_MODE', 'full'),
            'database_configured': bool(settings.DATABASES.get('default', {}).get('NAME')),
            'redis_configured': bool(getattr(settings, 'REDIS_URL', '')),
            'redis_required': bool(getattr(settings, 'REDIS_REQUIRED', True)),
        }
        serializer = HealthCheckSerializer(payload)
        return Response(serializer.data)
