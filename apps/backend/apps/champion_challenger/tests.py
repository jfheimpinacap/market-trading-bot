from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.champion_challenger.models import ChallengerRecommendationCode, ShadowComparisonResult
from apps.champion_challenger.services.bindings import create_challenger_binding, get_or_create_champion_binding
from apps.champion_challenger.services.recommendation import generate_recommendation
from apps.markets.models import Market, MarketSnapshot, MarketSourceType, MarketStatus, Provider
from apps.replay_lab.models import ReplayRun, ReplayRunStatus


class ChampionChallengerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_binding_construction(self):
        champion = get_or_create_champion_binding()
        self.assertTrue(champion.is_champion)
        challenger = create_challenger_binding(name='candidate_v2', overrides={'execution_profile': 'conservative_paper'})
        self.assertFalse(challenger.is_champion)
        self.assertEqual(challenger.execution_profile, 'conservative_paper')

    def test_recommendation_generation(self):
        code, reasons = generate_recommendation(
            comparison={
                'champion_metrics': {'proposal_ready_count': 10},
                'challenger_metrics': {'proposal_ready_count': 12},
                'decision_divergence_rate': 0.2,
                'deltas': {
                    'execution_adjusted_pnl_delta': '12.5',
                    'drawdown_proxy_delta': -0.01,
                    'fill_rate_delta': 0.03,
                    'risk_review_pressure_delta': 0.01,
                },
            }
        )
        self.assertEqual(code, ChallengerRecommendationCode.CHALLENGER_PROMISING)
        self.assertIn('better execution-adjusted pnl', reasons)

    def _seed_replay_environment(self):
        provider = Provider.objects.create(name='Kalshi', slug='kalshi', is_active=True)
        market = Market.objects.create(
            provider=provider,
            title='CC replay market',
            slug='cc-replay-market',
            source_type=MarketSourceType.REAL_READ_ONLY,
            is_active=True,
            status=MarketStatus.OPEN,
            current_yes_price=Decimal('54.0'),
            current_no_price=Decimal('46.0'),
        )
        now = timezone.now()
        for idx in range(4):
            MarketSnapshot.objects.create(
                market=market,
                captured_at=now - timedelta(minutes=30 - idx * 5),
                market_probability=Decimal('0.54'),
                yes_price=Decimal('54.0'),
                no_price=Decimal('46.0'),
                liquidity=Decimal('1200'),
                volume_24h=Decimal('350'),
            )

    def test_run_shadow_comparison_basic(self):
        self._seed_replay_environment()
        base_time = timezone.now()
        champion_replay = ReplayRun.objects.create(
            status=ReplayRunStatus.SUCCESS,
            source_scope='mixed',
            provider_scope='all',
            replay_start_at=base_time - timedelta(hours=1),
            replay_end_at=base_time,
            markets_considered=8,
            proposals_generated=10,
            trades_executed=6,
            approvals_required=2,
            blocked_count=2,
            total_pnl=Decimal('30.00'),
            ending_equity=Decimal('10030.00'),
            details={'execution_impact_summary': {'fill_rate': 0.6, 'partial_fill_rate': 0.2, 'no_fill_rate': 0.2, 'execution_adjusted_pnl': '30.00', 'execution_drag': '3.00'}},
        )
        challenger_replay = ReplayRun.objects.create(
            status=ReplayRunStatus.SUCCESS,
            source_scope='mixed',
            provider_scope='all',
            replay_start_at=base_time - timedelta(hours=1),
            replay_end_at=base_time,
            markets_considered=8,
            proposals_generated=12,
            trades_executed=8,
            approvals_required=1,
            blocked_count=1,
            total_pnl=Decimal('48.00'),
            ending_equity=Decimal('10048.00'),
            details={'execution_impact_summary': {'fill_rate': 0.7, 'partial_fill_rate': 0.15, 'no_fill_rate': 0.15, 'execution_adjusted_pnl': '48.00', 'execution_drag': '2.00'}},
        )

        with patch('apps.champion_challenger.services.shadow_runner.run_replay') as mock_replay:
            mock_replay.side_effect = [type('R', (), {'run': champion_replay})(), type('R', (), {'run': challenger_replay})()]
            response = self.client.post(reverse('champion_challenger:run'), {'lookback_hours': 12, 'challenger_overrides': {'execution_profile': 'conservative_paper'}}, format='json')

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['status'], 'COMPLETED')
        self.assertIn('recommendation_code', payload)
        self.assertTrue(ShadowComparisonResult.objects.filter(run_id=payload['id']).exists())

    def test_current_champion_and_summary_endpoints(self):
        champion_response = self.client.get(reverse('champion_challenger:current-champion'))
        self.assertEqual(champion_response.status_code, 200)

        summary_response = self.client.get(reverse('champion_challenger:summary'))
        self.assertEqual(summary_response.status_code, 200)
        data = summary_response.json()
        self.assertIn('current_champion', data)
        self.assertIn('recent_runs', data)
