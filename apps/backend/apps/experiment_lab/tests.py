from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.evaluation_lab.models import EvaluationMetricSet, EvaluationRun
from apps.experiment_lab.models import StrategyProfile
from apps.experiment_lab.services import seed_strategy_profiles
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
