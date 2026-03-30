from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.evaluation_lab.models import EffectivenessMetric, EffectivenessMetricType, EffectivenessMetricStatus, EvaluationRuntimeRun
from apps.experiment_lab.models import ExperimentCandidate, ExperimentPromotionRecommendation, TuningChampionChallengerComparison
from apps.experiment_lab.models import StrategyProfile
from apps.experiment_lab.services import seed_strategy_profiles
from apps.tuning_board.models import TuningComponent, TuningPriorityLevel, TuningProposal, TuningProposalStatus, TuningProposalType, TuningReviewRun, TuningScope
from apps.markets.models import Market, MarketSnapshot, MarketSourceType, MarketStatus, Provider


class ExperimentLabTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        seed_strategy_profiles()

    def _seed_replay_snapshots(self):
        provider = Provider.objects.create(name='Kalshi', slug='kalshi', is_active=True)
        market = Market.objects.create(
            provider=provider,
            title='Experiment replay market',
            slug='experiment-replay-market',
            source_type=MarketSourceType.REAL_READ_ONLY,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('52.0'),
            current_no_price=Decimal('48.0'),
        )
        now = timezone.now()
        for idx in range(3):
            MarketSnapshot.objects.create(
                market=market,
                captured_at=now - timedelta(minutes=30 - idx * 5),
                market_probability=Decimal('0.52'),
                yes_price=Decimal('52.0'),
                no_price=Decimal('48.0'),
                liquidity=Decimal('1000'),
                volume_24h=Decimal('250'),
            )

    def test_strategy_profile_seed(self):
        response = self.client.post(reverse('experiment_lab:seed-profiles'), {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(StrategyProfile.objects.count(), 5)

    def test_experiment_run_replay(self):
        self._seed_replay_snapshots()
        profile = StrategyProfile.objects.get(slug='balanced')
        now = timezone.now()
        payload = {
            'strategy_profile_id': profile.id,
            'run_type': 'replay',
            'provider_scope': 'kalshi',
            'start_timestamp': (now - timedelta(hours=2)).isoformat(),
            'end_timestamp': now.isoformat(),
        }
        response = self.client.post(reverse('experiment_lab:run'), payload, format='json')
        self.assertIn(response.status_code, [201, 400])
        runs_response = self.client.get(reverse('experiment_lab:runs'))
        self.assertEqual(runs_response.status_code, 200)
        self.assertGreaterEqual(len(runs_response.json()), 1)

    def test_experiment_comparison_endpoint(self):
        profile = StrategyProfile.objects.get(slug='balanced')
        eval_run = EvaluationRun.objects.create(status='READY', summary='Eval run')
        EvaluationMetricSet.objects.create(
            run=eval_run,
            proposals_generated=10,
            trades_executed_count=4,
            approval_required_count=3,
            blocked_count=2,
            total_pnl=Decimal('20.00'),
            ending_equity=Decimal('10020.00'),
            equity_delta=Decimal('20.00'),
        )

        left = self.client.post(reverse('experiment_lab:run'), {'strategy_profile_id': profile.id, 'run_type': 'live_eval'}, format='json').json()

        eval_run_2 = EvaluationRun.objects.create(status='READY', summary='Eval run 2')
        EvaluationMetricSet.objects.create(
            run=eval_run_2,
            proposals_generated=12,
            trades_executed_count=5,
            approval_required_count=2,
            blocked_count=1,
            total_pnl=Decimal('35.00'),
            ending_equity=Decimal('10035.00'),
            equity_delta=Decimal('35.00'),
        )
        right = self.client.post(reverse('experiment_lab:run'), {'strategy_profile_id': profile.id, 'run_type': 'live_eval'}, format='json').json()

        comparison = self.client.get(
            reverse('experiment_lab:comparison'),
            {'left_run_id': left['id'], 'right_run_id': right['id']},
        )
        self.assertEqual(comparison.status_code, 200)
        payload = comparison.json()
        self.assertIn('delta', payload)
        self.assertIn('interpretation', payload)

    def test_summary_endpoint(self):
        profile = StrategyProfile.objects.get(slug='conservative')
        self.client.post(reverse('experiment_lab:run'), {'strategy_profile_id': profile.id, 'run_type': 'live_session_compare'}, format='json')
        summary = self.client.get(reverse('experiment_lab:summary'))
        self.assertEqual(summary.status_code, 200)
        self.assertIn('recent_runs', summary.json())

    def test_comparison_includes_execution_aware_delta(self):
        self._seed_replay_snapshots()
        profile = StrategyProfile.objects.get(slug='balanced')
        now = timezone.now()
        base_payload = {
            'strategy_profile_id': profile.id,
            'run_type': 'replay',
            'provider_scope': 'kalshi',
            'start_timestamp': (now - timedelta(hours=2)).isoformat(),
            'end_timestamp': now.isoformat(),
        }
        left = self.client.post(
            reverse('experiment_lab:run'),
            {**base_payload, 'execution_mode': 'naive'},
            format='json',
        ).json()
        right = self.client.post(
            reverse('experiment_lab:run'),
            {**base_payload, 'execution_mode': 'execution_aware', 'execution_profile': 'balanced_paper'},
            format='json',
        ).json()
        comparison = self.client.get(
            reverse('experiment_lab:comparison'),
            {'left_run_id': left['id'], 'right_run_id': right['id']},
        )
        self.assertEqual(comparison.status_code, 200)
        payload = comparison.json()
        self.assertIn('execution_comparison', payload)

    def _create_tuning_proposal(self, *, sample_count: int, metric_type: str, metric_value: Decimal, baseline_value: Decimal, status: str = TuningProposalStatus.READY_FOR_REVIEW):
        eval_runtime = EvaluationRuntimeRun.objects.create(metric_count=1, recommendation_summary={}, metadata={})
        metric = EffectivenessMetric.objects.create(
            run=eval_runtime,
            metric_type=metric_type,
            metric_scope='global',
            metric_value=metric_value,
            sample_count=sample_count,
            status=EffectivenessMetricStatus.POOR,
            metadata={'baseline_value': str(baseline_value)},
        )
        tuning_run = TuningReviewRun.objects.create(metadata={'source': 'test'})
        return TuningProposal.objects.create(
            run=tuning_run,
            source_metric=metric,
            proposal_type=TuningProposalType.CALIBRATION_BIAS_OFFSET,
            target_scope=TuningScope.GLOBAL,
            target_component=TuningComponent.CALIBRATION,
            proposal_status=status,
            evidence_strength_score=Decimal('0.8'),
            priority_level=TuningPriorityLevel.HIGH,
            rationale='Calibrate probability bias in paper runtime.',
        )

    def test_run_tuning_validation_builds_candidates_and_summary(self):
        self._create_tuning_proposal(
            sample_count=80,
            metric_type=EffectivenessMetricType.CALIBRATION_ERROR,
            metric_value=Decimal('0.08'),
            baseline_value=Decimal('0.10'),
        )
        run_response = self.client.post(reverse('experiment_lab:run-tuning-validation'), {'metadata': {'triggered_from': 'tests'}}, format='json')
        self.assertEqual(run_response.status_code, 201)
        self.assertEqual(ExperimentCandidate.objects.count(), 1)
        self.assertEqual(TuningChampionChallengerComparison.objects.count(), 1)
        self.assertEqual(ExperimentPromotionRecommendation.objects.count(), 1)

        summary = self.client.get(reverse('experiment_lab:tuning-validation-summary'))
        self.assertEqual(summary.status_code, 200)
        payload = summary.json()
        self.assertEqual(payload['candidates_reviewed'], 1)
        self.assertEqual(payload['comparisons_run'], 1)

    def test_run_tuning_validation_marks_needs_more_data_when_sample_is_low(self):
        self._create_tuning_proposal(
            sample_count=10,
            metric_type=EffectivenessMetricType.BRIER_SCORE,
            metric_value=Decimal('0.25'),
            baseline_value=Decimal('0.20'),
        )
        self.client.post(reverse('experiment_lab:run-tuning-validation'), {'metadata': {}}, format='json')
        comparison = TuningChampionChallengerComparison.objects.latest('id')
        recommendation = ExperimentPromotionRecommendation.objects.latest('id')
        self.assertEqual(comparison.comparison_status, 'NEEDS_MORE_DATA')
        self.assertEqual(recommendation.recommendation_type, 'REQUIRE_MORE_DATA')

    def test_tuning_validation_lists_support_filters(self):
        self._create_tuning_proposal(
            sample_count=90,
            metric_type=EffectivenessMetricType.RISK_APPROVAL_PRECISION,
            metric_value=Decimal('0.62'),
            baseline_value=Decimal('0.55'),
            status=TuningProposalStatus.WATCH,
        )
        self.client.post(reverse('experiment_lab:run-tuning-validation'), {'metadata': {}}, format='json')
        candidates = self.client.get(reverse('experiment_lab:tuning-candidates'), {'readiness_status': 'NEEDS_MORE_DATA'})
        self.assertEqual(candidates.status_code, 200)
        self.assertGreaterEqual(len(candidates.json()), 1)
