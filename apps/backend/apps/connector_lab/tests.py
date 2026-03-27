from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.connector_lab.models import AdapterReadinessCode
from apps.connector_lab.services import ensure_fixture_profiles, execute_qualification_suite, get_fixture_profile


class ConnectorLabServiceTests(TestCase):
    def setUp(self):
        ensure_fixture_profiles()

    def test_qualification_run_basic(self):
        fixture = get_fixture_profile('generic_binary_market_fixture')
        run = execute_qualification_suite(fixture_profile=fixture)
        self.assertGreater(run.results.count(), 0)
        self.assertIn(run.qualification_status, {'SUCCESS', 'PARTIAL', 'FAILED'})
        self.assertIsNotNone(run.readiness_recommendation)

    def test_capability_failure_detected_as_unsupported_or_partial(self):
        fixture = get_fixture_profile('unsupported_capability_fixture')
        run = execute_qualification_suite(fixture_profile=fixture)
        unsupported_or_failed = run.results.filter(case_code='unsupported_order_type').first()
        self.assertIsNotNone(unsupported_or_failed)
        self.assertIn(unsupported_or_failed.result_status, {'UNSUPPORTED', 'WARNING', 'FAILED'})

    def test_recommendation_generation(self):
        fixture = get_fixture_profile('rejection_fixture')
        run = execute_qualification_suite(fixture_profile=fixture)
        self.assertIn(
            run.readiness_recommendation.recommendation,
            {
                AdapterReadinessCode.SANDBOX_CERTIFIED,
                AdapterReadinessCode.READ_ONLY_PREPARED,
                AdapterReadinessCode.INCOMPLETE_MAPPING,
                AdapterReadinessCode.RECONCILIATION_GAPS,
                AdapterReadinessCode.MANUAL_REVIEW_REQUIRED,
                AdapterReadinessCode.NOT_READY,
            },
        )


class ConnectorLabApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_connector_lab_endpoints(self):
        cases = self.client.get(reverse('connector_lab:cases'))
        self.assertEqual(cases.status_code, 200)

        run = self.client.post(
            reverse('connector_lab:run-qualification'),
            {'fixture_profile': 'generic_binary_market_fixture', 'metadata': {'triggered_from': 'test'}},
            format='json',
        )
        self.assertEqual(run.status_code, 201)
        run_id = run.data['id']

        runs = self.client.get(reverse('connector_lab:runs'))
        run_detail = self.client.get(reverse('connector_lab:run-detail', kwargs={'pk': run_id}))
        readiness = self.client.get(reverse('connector_lab:current-readiness'))
        summary = self.client.get(reverse('connector_lab:summary'))

        self.assertEqual(runs.status_code, 200)
        self.assertEqual(run_detail.status_code, 200)
        self.assertEqual(readiness.status_code, 200)
        self.assertEqual(summary.status_code, 200)
