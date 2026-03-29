from django.test import TestCase
from django.urls import reverse

from apps.autonomy_package.tests import AutonomyPackageTests
from apps.autonomy_seed.models import GovernanceSeed


class AutonomySeedTests(AutonomyPackageTests):
    def _create_adopted_package(self, *, target='roadmap') -> int:
        decision_id = self._emit_registered_decision(target=target)
        package_response = self.client.post(reverse('autonomy_package:register', args=[decision_id]), data={}, content_type='application/json')
        self.assertEqual(package_response.status_code, 200)
        package_id = package_response.json()['package_id']
        adopt_response = self.client.post(reverse('autonomy_package_review:adopt', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(adopt_response.status_code, 200)
        return package_id

    def test_candidates_only_include_adopted_packages(self):
        package_id = self._create_adopted_package(target='roadmap')
        response = self.client.get(reverse('autonomy_seed:candidates'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(row['governance_package'] == package_id for row in payload))

    def test_register_creates_seed_types(self):
        roadmap = self._create_adopted_package(target='roadmap')
        scenario = self._create_adopted_package(target='scenario')
        program = self._create_adopted_package(target='program')

        self.client.post(reverse('autonomy_seed:register', args=[roadmap]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_seed:register', args=[scenario]), data={}, content_type='application/json')
        self.client.post(reverse('autonomy_seed:register', args=[program]), data={}, content_type='application/json')

        seeds = self.client.get(reverse('autonomy_seed:seeds')).json()
        seed_types = {row['seed_type'] for row in seeds}
        self.assertIn('ROADMAP_SEED', seed_types)
        self.assertIn('SCENARIO_SEED', seed_types)
        self.assertIn('PROGRAM_SEED', seed_types)

    def test_duplicate_registration_is_skipped(self):
        package_id = self._create_adopted_package(target='roadmap')
        first = self.client.post(reverse('autonomy_seed:register', args=[package_id]), data={}, content_type='application/json')
        second = self.client.post(reverse('autonomy_seed:register', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['seed_status'], 'DUPLICATE_SKIPPED')

    def test_register_requires_blocker_free_package_resolution(self):
        package_id = self._create_adopted_package(target='manager')
        from apps.autonomy_package_review.models import PackageResolution

        resolution = PackageResolution.objects.get(governance_package_id=package_id)
        resolution.blockers = ['requires_context']
        resolution.save(update_fields=['blockers', 'updated_at'])

        response = self.client.post(reverse('autonomy_seed:register', args=[package_id]), data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_summary_endpoint(self):
        self._create_adopted_package(target='operator_review')
        self.client.post(reverse('autonomy_seed:run_review'), data={}, content_type='application/json')
        response = self.client.get(reverse('autonomy_seed:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('candidate_count', payload)
        self.assertIn('recommendation_summary', payload)
        self.assertTrue(GovernanceSeed.objects.exists())
