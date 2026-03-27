from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.experiment_lab.models import ExperimentRun, StrategyProfile
from apps.operator_queue.models import OperatorQueueItem
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile
from apps.readiness_lab.services import seed_readiness_profiles
from apps.replay_lab.models import ReplayRun


class ReadinessLabTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        seed_readiness_profiles()

    def _seed_operational_data(self):
        run = EvaluationRun.objects.create(status='READY', summary='Eval for readiness')
        EvaluationMetricSet.objects.create(
            run=run,
            favorable_review_rate=Decimal('0.68'),
            block_rate=Decimal('0.15'),
            safety_events_count=1,
            hard_stop_count=0,
            equity_delta=Decimal('25.00'),
        )

        ReplayRun.objects.create(
            status='SUCCESS',
            replay_start_at=run.started_at,
            replay_end_at=run.started_at,
            summary='Replay run 1',
        )
        ReplayRun.objects.create(
            status='SUCCESS',
            replay_start_at=run.started_at,
            replay_end_at=run.started_at,
            summary='Replay run 2',
        )

        profile = StrategyProfile.objects.create(name='Readiness test profile', slug='readiness-test-profile', config={})
        ExperimentRun.objects.create(strategy_profile=profile, run_type='live_session_compare', status='SUCCESS', normalized_metrics={'consistency_band': 'good'})
        OperatorQueueItem.objects.create(headline='Approval needed', status='APPROVED')

    def test_seed_readiness_profiles_endpoint(self):
        response = self.client.post(reverse('readiness_lab:seed-profiles'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(ReadinessProfile.objects.count(), 3)

    def test_assessment_endpoint_creates_run(self):
        self._seed_operational_data()
        profile = ReadinessProfile.objects.get(slug='readiness-balanced')
        response = self.client.post(reverse('readiness_lab:assess'), {'readiness_profile_id': profile.id}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ReadinessAssessmentRun.objects.count(), 1)
        self.assertIn(response.json()['status'], ['READY', 'CAUTION', 'NOT_READY'])

    def test_gates_fail_when_data_missing(self):
        profile = ReadinessProfile.objects.get(slug='readiness-strict')
        response = self.client.post(reverse('readiness_lab:assess'), {'readiness_profile_id': profile.id}, format='json')
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['status'], 'NOT_READY')
        self.assertGreater(payload['gates_failed_count'], 0)

    def test_summary_and_run_detail_endpoints(self):
        self._seed_operational_data()
        profile = ReadinessProfile.objects.get(slug='readiness-conservative')
        run_response = self.client.post(reverse('readiness_lab:assess'), {'readiness_profile_id': profile.id}, format='json')
        run_id = run_response.json()['id']

        summary = self.client.get(reverse('readiness_lab:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()['total_runs'], 1)

        detail = self.client.get(reverse('readiness_lab:run-detail', kwargs={'pk': run_id}))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['id'], run_id)

    def test_readiness_includes_execution_impact_summary(self):
        profile = ReadinessProfile.objects.get(slug='readiness-balanced')
        response = self.client.post(reverse('readiness_lab:assess'), {'readiness_profile_id': profile.id}, format='json')
        self.assertEqual(response.status_code, 201)
        execution_summary = response.json().get('details', {}).get('execution_impact_summary', {})
        self.assertIn('execution_aware_runs', execution_summary)
        self.assertIn('summary', execution_summary)
