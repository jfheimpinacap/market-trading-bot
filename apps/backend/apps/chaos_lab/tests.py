from django.test import TestCase
from django.urls import reverse

from apps.chaos_lab.models import ChaosExperiment, ChaosObservation, ChaosRun, ResilienceBenchmark
from apps.chaos_lab.services.experiments import ensure_default_experiments
from apps.incident_commander.models import IncidentRecord


class ChaosLabTests(TestCase):
    def test_seed_experiments_and_run_baseline_scenario(self):
        seeded = ensure_default_experiments()
        self.assertGreaterEqual(seeded['total'], 6)

        experiment = ChaosExperiment.objects.get(slug='provider-sync-failure')
        response = self.client.post(
            reverse('chaos_lab:run'),
            {'experiment_id': experiment.id, 'trigger_mode': 'manual'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, {201, 400})

        run = ChaosRun.objects.order_by('-id').first()
        self.assertIsNotNone(run)
        self.assertIn(run.status, {'SUCCESS', 'PARTIAL', 'FAILED'})
        self.assertTrue(ChaosObservation.objects.filter(run=run).exists())

    def test_benchmark_consolidation_and_incident_integration(self):
        ensure_default_experiments()
        experiment = ChaosExperiment.objects.get(slug='mission-control-step-failure')
        self.client.post(reverse('chaos_lab:run'), {'experiment_id': experiment.id}, content_type='application/json')

        run = ChaosRun.objects.order_by('-id').first()
        self.assertIsNotNone(run)
        self.assertTrue(ResilienceBenchmark.objects.filter(run=run).exists())

        benchmark = ResilienceBenchmark.objects.get(run=run)
        self.assertGreaterEqual(float(benchmark.resilience_score), 0)
        self.assertLessEqual(float(benchmark.resilience_score), 100)
        self.assertGreaterEqual(IncidentRecord.objects.count(), 1)

    def test_main_endpoints(self):
        ensure_default_experiments()
        experiments_res = self.client.get(reverse('chaos_lab:experiments'))
        self.assertEqual(experiments_res.status_code, 200)
        experiment_id = experiments_res.json()[0]['id']

        run_res = self.client.post(reverse('chaos_lab:run'), {'experiment_id': experiment_id}, content_type='application/json')
        self.assertIn(run_res.status_code, {201, 400})

        runs_res = self.client.get(reverse('chaos_lab:runs'))
        summary_res = self.client.get(reverse('chaos_lab:summary'))
        benchmarks_res = self.client.get(reverse('chaos_lab:benchmarks'))

        self.assertEqual(runs_res.status_code, 200)
        self.assertEqual(summary_res.status_code, 200)
        self.assertEqual(benchmarks_res.status_code, 200)

        runs = runs_res.json()
        if runs:
            detail_res = self.client.get(reverse('chaos_lab:run-detail', args=[runs[0]['id']]))
            self.assertEqual(detail_res.status_code, 200)
