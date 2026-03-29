from django.test import TestCase
from django.urls import reverse

from apps.autonomy_package.tests import AutonomyPackageTests
from apps.autonomy_package_review.models import PackageResolution


class AutonomyPackageReviewTests(AutonomyPackageTests):
    def _create_registered_package(self, *, target='roadmap') -> int:
        decision_id = self._emit_registered_decision(target=target)
        response = self.client.post(reverse('autonomy_package:register', args=[decision_id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response.json()['package_id']

    def test_candidates_only_include_registered_ready_ack_or_blocked(self):
        self._create_registered_package(target='roadmap')
        response = self.client.get(reverse('autonomy_package_review:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 1)
        self.assertTrue(all(row['package_status'] in {'REGISTERED', 'READY', 'ACKNOWLEDGED', 'BLOCKED'} for row in payload))

    def test_acknowledge_action_is_audited(self):
        package_id = self._create_registered_package(target='scenario')
        response = self.client.post(reverse('autonomy_package_review:acknowledge', args=[package_id]), data={'actor': 'test-operator'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['resolution_status'], 'ACKNOWLEDGED')

    def test_adopt_action_is_audited(self):
        package_id = self._create_registered_package(target='program')
        response = self.client.post(reverse('autonomy_package_review:adopt', args=[package_id]), data={'actor': 'test-operator'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['resolution_status'], 'ADOPTED')

    def test_run_review_does_not_override_adopted(self):
        package_id = self._create_registered_package(target='manager')
        self.client.post(reverse('autonomy_package_review:adopt', args=[package_id]), data={}, content_type='application/json')
        run_response = self.client.post(reverse('autonomy_package_review:run_review'), data={}, content_type='application/json')
        self.assertEqual(run_response.status_code, 200)

        resolutions = self.client.get(reverse('autonomy_package_review:resolutions')).json()
        row = next(item for item in resolutions if item['governance_package'] == package_id)
        self.assertEqual(row['resolution_status'], 'ADOPTED')

    def test_summary_endpoint(self):
        self._create_registered_package(target='operator_review')
        self.client.post(reverse('autonomy_package_review:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_package_review:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)

    def test_reject_and_defer_actions_are_supported(self):
        package_id = self._create_registered_package(target='roadmap')
        defer_response = self.client.post(reverse('autonomy_package_review:defer', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(defer_response.status_code, 200)
        self.assertEqual(defer_response.json()['resolution_status'], 'DEFERRED')

        reject_response = self.client.post(reverse('autonomy_package_review:reject', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()['resolution_status'], 'REJECTED')
        self.assertEqual(PackageResolution.objects.get(governance_package_id=package_id).resolution_status, 'REJECTED')
