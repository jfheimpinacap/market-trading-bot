from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.champion_challenger.models import ChampionChallengerRun, ChampionChallengerRunStatus, ShadowComparisonResult
from apps.champion_challenger.services.bindings import create_challenger_binding, get_or_create_champion_binding
from apps.portfolio_governor.models import PortfolioGovernanceRun, PortfolioThrottleDecision
from apps.prediction_training.models import PredictionDatasetRun, PredictionModelArtifact, PredictionTrainingRun
from apps.promotion_committee.models import PromotionRecommendationCode
from apps.promotion_committee.services.evidence import build_stack_evidence_snapshot
from apps.promotion_committee.services.recommendation import generate_recommendation
from apps.readiness_lab.models import ReadinessAssessmentRun, ReadinessProfile, ReadinessStatus


class PromotionCommitteeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.champion = get_or_create_champion_binding()
        self.challenger = create_challenger_binding(name='pc_challenger', overrides={'execution_profile': 'conservative_paper'})

    def _seed_supporting_data(self, readiness_status=ReadinessStatus.READY, markets=14, pnl_delta='4.0'):
        profile = ReadinessProfile.objects.create(name='default', slug='default', config={})
        ReadinessAssessmentRun.objects.create(
            readiness_profile=profile,
            status=readiness_status,
            overall_score=Decimal('0.8'),
            summary='ready',
            details={},
        )

        run = ChampionChallengerRun.objects.create(
            champion_binding=self.champion,
            challenger_binding=self.challenger,
            status=ChampionChallengerRunStatus.COMPLETED,
            markets_evaluated=markets,
            opportunities_compared=markets,
            proposals_compared=markets,
            fills_compared=markets,
            recommendation_code='CHALLENGER_PROMISING',
            recommendation_reasons=['positive_delta'],
            summary='good delta',
        )
        ShadowComparisonResult.objects.create(
            run=run,
            champion_metrics={'fill_rate': 0.6},
            challenger_metrics={'fill_rate': 0.66},
            deltas={
                'execution_adjusted_pnl_delta': pnl_delta,
                'fill_rate_delta': 0.05,
                'no_fill_rate_delta': -0.02,
                'execution_drag_delta': -0.02,
                'drawdown_proxy_delta': -0.01,
                'risk_review_pressure_delta': 0.01,
            },
            decision_divergence_rate=Decimal('0.12'),
        )

        throttle = PortfolioThrottleDecision.objects.create(state='NORMAL', reason_codes=[], rationale='ok')
        PortfolioGovernanceRun.objects.create(status='COMPLETED', throttle_decision=throttle, summary='ok')

        dataset = PredictionDatasetRun.objects.create(
            name='ds',
            label_definition='up/down',
            started_at='2026-03-01T00:00:00Z',
            feature_set_version='v1',
        )
        training = PredictionTrainingRun.objects.create(dataset_run=dataset, started_at='2026-03-01T00:00:00Z', status='success')
        PredictionModelArtifact.objects.create(
            name='xgb',
            version='1',
            training_run=training,
            label_definition='up/down',
            feature_set_version='v1',
            artifact_path='/tmp/model.bin',
            is_active=True,
        )

    def test_evidence_snapshot_basic(self):
        self._seed_supporting_data()
        snapshot = build_stack_evidence_snapshot(challenger_binding_id=self.challenger.id)
        self.assertEqual(snapshot.champion_binding.id, self.champion.id)
        self.assertEqual(snapshot.challenger_binding.id, self.challenger.id)
        self.assertIn('status', snapshot.readiness_summary)

    def test_recommendation_keep_current_champion(self):
        self._seed_supporting_data(readiness_status=ReadinessStatus.READY, markets=20, pnl_delta='-3.0')
        snapshot = build_stack_evidence_snapshot(challenger_binding_id=self.challenger.id)
        recommendation = generate_recommendation(snapshot)
        self.assertEqual(recommendation.code, PromotionRecommendationCode.KEEP_CURRENT_CHAMPION)

    def test_recommendation_extend_shadow_test(self):
        self._seed_supporting_data(readiness_status=ReadinessStatus.CAUTION, markets=8, pnl_delta='6.0')
        snapshot = build_stack_evidence_snapshot(challenger_binding_id=self.challenger.id)
        recommendation = generate_recommendation(snapshot)
        self.assertEqual(recommendation.code, PromotionRecommendationCode.EXTEND_SHADOW_TEST)

    def test_blocking_by_readiness_constraints(self):
        self._seed_supporting_data(readiness_status=ReadinessStatus.NOT_READY, markets=20, pnl_delta='10.0')
        response = self.client.post(reverse('promotion_committee:run-review'), {'challenger_binding_id': self.challenger.id}, format='json')
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload['recommendation_code'], PromotionRecommendationCode.REVERT_TO_CONSERVATIVE_STACK)

    def test_manual_apply_promotes_challenger(self):
        self._seed_supporting_data(readiness_status=ReadinessStatus.READY, markets=20, pnl_delta='10.0')
        create_res = self.client.post(
            reverse('promotion_committee:run-review'),
            {'challenger_binding_id': self.challenger.id, 'decision_mode': 'MANUAL_APPLY'},
            format='json',
        )
        self.assertEqual(create_res.status_code, 201)
        run_id = create_res.json()['id']
        apply_res = self.client.post(reverse('promotion_committee:apply', kwargs={'pk': run_id}), {'actor': 'tester'}, format='json')
        self.assertEqual(apply_res.status_code, 200)

    def test_core_endpoints(self):
        self._seed_supporting_data()
        self.client.post(reverse('promotion_committee:run-review'), {'challenger_binding_id': self.challenger.id}, format='json')

        runs_res = self.client.get(reverse('promotion_committee:runs'))
        self.assertEqual(runs_res.status_code, 200)
        current_res = self.client.get(reverse('promotion_committee:current-recommendation'))
        self.assertEqual(current_res.status_code, 200)
        summary_res = self.client.get(reverse('promotion_committee:summary'))
        self.assertEqual(summary_res.status_code, 200)
