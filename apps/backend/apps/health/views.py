from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        payload = {
            'status': 'ok',
            'service': 'market-trading-bot-backend',
            'environment': 'development' if settings.DEBUG else 'production',
            'dependencies': {
                'database': settings.DATABASES['default']['ENGINE'],
                'broker': settings.CELERY_BROKER_URL,
            },
        }
        return Response(payload)
