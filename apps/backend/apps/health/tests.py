from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthCheckTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_healthcheck_returns_expected_payload(self):
        response = self.client.get(reverse('health:health-check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['service'], 'market-trading-bot-backend')
        self.assertIn('environment', response.json())
        self.assertIn('database_configured', response.json())
        self.assertIn('redis_configured', response.json())

    def test_healthcheck_is_available_under_api_prefix(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
