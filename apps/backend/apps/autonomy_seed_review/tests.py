from django.urls import reverse

from apps.autonomy_package.tests import AutonomyPackageTests
from apps.autonomy_seed_review.models import SeedResolution


class AutonomySeedReviewTests(AutonomyPackageTests):
    def _create_registered_seed(self, *, target='roadmap') -> int:
        decision_id = self._emit_registered_decision(target=target)
        package_response = self.client.post(reverse('autonomy_package:register', args=[decision_id]), data={}, content_type='application/json')
        package_id = package_response.json()['package_id']
        self.client.post(reverse('autonomy_package_review:adopt', args=[package_id]), data={}, content_type='application/json')
        response = self.client.post(reverse('autonomy_seed:register', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return response.json()['seed_id']

    def test_candidates_include_registered_seeds(self):
        seed_id = self._create_registered_seed()
        response = self.client.get(reverse('autonomy_seed_review:candidates'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(row['governance_seed'] == seed_id for row in response.json()))

    def test_accept_does_not_duplicate_closed_resolution(self):
        seed_id = self._create_registered_seed()
        self.client.post(reverse('autonomy_seed_review:accept', args=[seed_id]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_seed_review:accept', args=[seed_id]), data={}, content_type='application/json')
        self.assertEqual(SeedResolution.objects.filter(governance_seed_id=seed_id).count(), 1)

    def test_acknowledge_seed_is_audited(self):
        seed_id = self._create_registered_seed(target='program')
        response = self.client.post(reverse('autonomy_seed_review:acknowledge', args=[seed_id]), data={'actor': 'qa-user'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        resolution = SeedResolution.objects.get(governance_seed_id=seed_id)
        self.assertEqual(resolution.resolution_status, 'ACKNOWLEDGED')
        self.assertEqual(resolution.resolved_by, 'qa-user')

    def test_accept_seed_is_audited(self):
        seed_id = self._create_registered_seed(target='scenario')
        response = self.client.post(reverse('autonomy_seed_review:accept', args=[seed_id]), data={'actor': 'qa-user'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        resolution = SeedResolution.objects.get(governance_seed_id=seed_id)
        self.assertEqual(resolution.resolution_status, 'ACCEPTED')
        self.assertEqual(resolution.resolved_by, 'qa-user')

    def test_defer_and_reject(self):
        defer_seed = self._create_registered_seed(target='manager')
        reject_seed = self._create_registered_seed(target='roadmap')
        defer_response = self.client.post(reverse('autonomy_seed_review:defer', args=[defer_seed]), data={}, content_type='application/json')
        reject_response = self.client.post(reverse('autonomy_seed_review:reject', args=[reject_seed]), data={}, content_type='application/json')
        self.assertEqual(defer_response.status_code, 200)
        self.assertEqual(reject_response.status_code, 200)

    def test_summary_endpoint(self):
        self._create_registered_seed()
        self.client.post(reverse('autonomy_seed_review:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_seed_review:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
