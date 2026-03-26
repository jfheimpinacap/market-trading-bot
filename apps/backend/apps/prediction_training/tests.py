from decimal import Decimal
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.models import Event, Market, MarketSnapshot, Provider
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.prediction_training.models import ModelComparisonRun, PredictionDatasetRun, PredictionModelArtifact, PredictionTrainingRun
from apps.prediction_training.services.dataset import build_prediction_dataset
from apps.prediction_training.services.registry import activate_model, get_active_model_artifact
from apps.research_agent.models import ResearchCandidate


class PredictionTrainingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.provider = Provider.objects.create(name='Kalshi', slug='kalshi')
        self.event = Event.objects.create(provider=self.provider, title='Training Event', slug='training-event')
        self.market = Market.objects.create(
            provider=self.provider,
            event=self.event,
            title='Will training complete?',
            slug='will-training-complete',
            current_market_probability=Decimal('0.4500'),
            source_type='demo',
            resolution_time=timezone.now() + timezone.timedelta(days=10),
        )
        start = timezone.now() - timezone.timedelta(hours=96)
        probs = ['0.41', '0.43', '0.47', '0.45', '0.50', '0.54', '0.52', '0.57', '0.60']
        for idx, prob in enumerate(probs):
            MarketSnapshot.objects.create(
                market=self.market,
                captured_at=start + timezone.timedelta(hours=idx * 12),
                market_probability=Decimal(prob),
                volume_24h=Decimal('1000.0') + idx,
                liquidity=Decimal('9000.0') + idx * 10,
            )
        ResearchCandidate.objects.create(
            market=self.market,
            narrative_pressure=Decimal('0.6500'),
            sentiment_direction='bullish',
            divergence_score=Decimal('0.1500'),
            implied_probability_snapshot=Decimal('0.4500'),
            market_implied_direction='neutral',
            short_thesis='positive drift',
            priority=Decimal('0.60'),
        )

    def test_dataset_build_persists_metadata(self):
        result = build_prediction_dataset(name='test_ds', horizon_hours=24)
        dataset = result.dataset_run
        self.assertGreater(dataset.rows_built, 0)
        self.assertEqual(dataset.status, 'success')
        self.assertTrue(Path(dataset.artifact_path).exists())
        self.assertEqual(dataset.label_definition, 'future_probability_up_24h')

    def test_api_build_dataset_and_list_runs(self):
        build_response = self.client.post(
            reverse('prediction_training:build-dataset'),
            {'name': 'api_ds', 'horizon_hours': 24},
            format='json',
        )
        self.assertEqual(build_response.status_code, 201)
        list_response = self.client.get(reverse('prediction_training:train-run-list'))
        self.assertEqual(list_response.status_code, 200)

    def test_model_registry_activate(self):
        dataset = PredictionDatasetRun.objects.create(
            name='manual',
            status='success',
            label_definition='future_probability_up_24h',
            feature_set_version='prediction_features_v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        run = PredictionTrainingRun.objects.create(
            status='success',
            dataset_run=dataset,
            model_type='xgboost',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        one = PredictionModelArtifact.objects.create(
            name='xgb',
            version='v1',
            model_type='xgboost',
            label_definition=dataset.label_definition,
            feature_set_version=dataset.feature_set_version,
            training_run=run,
            validation_metrics={'accuracy': 0.5},
            artifact_path='/tmp/missing.joblib',
        )
        two = PredictionModelArtifact.objects.create(
            name='xgb',
            version='v2',
            model_type='xgboost',
            label_definition=dataset.label_definition,
            feature_set_version=dataset.feature_set_version,
            training_run=run,
            validation_metrics={'accuracy': 0.6},
            artifact_path='/tmp/missing2.joblib',
        )
        activate_model(artifact=one)
        activate_model(artifact=two)
        self.assertEqual(get_active_model_artifact().id, two.id)
        one.refresh_from_db()
        self.assertFalse(one.is_active)

    def test_inference_fallback_to_heuristic_on_broken_active_model(self):
        dataset = PredictionDatasetRun.objects.create(
            name='manual',
            status='success',
            label_definition='future_probability_up_24h',
            feature_set_version='prediction_features_v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        run = PredictionTrainingRun.objects.create(
            status='success',
            dataset_run=dataset,
            model_type='xgboost',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        artifact = PredictionModelArtifact.objects.create(
            name='xgb',
            version='broken',
            model_type='xgboost',
            label_definition=dataset.label_definition,
            feature_set_version=dataset.feature_set_version,
            training_run=run,
            validation_metrics={'accuracy': 0.5},
            artifact_path='/tmp/does-not-exist.joblib',
            is_active=True,
        )

        scored = score_market_prediction(market=self.market, profile_slug='heuristic_baseline', triggered_by='test')
        self.assertIsNotNone(scored.score.id)
        self.assertIn('heuristic_fallback', scored.score.details.get('model_runtime', {}).get('runtime_mode', ''))

    def test_api_model_activation_endpoints(self):
        dataset = PredictionDatasetRun.objects.create(
            name='manual',
            status='success',
            label_definition='future_probability_up_24h',
            feature_set_version='prediction_features_v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        run = PredictionTrainingRun.objects.create(
            status='success',
            dataset_run=dataset,
            model_type='xgboost',
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        artifact = PredictionModelArtifact.objects.create(
            name='xgb',
            version='v1',
            model_type='xgboost',
            label_definition=dataset.label_definition,
            feature_set_version=dataset.feature_set_version,
            training_run=run,
            validation_metrics={'accuracy': 0.5},
            artifact_path='/tmp/nope.joblib',
        )
        response = self.client.post(reverse('prediction_training:model-activate', kwargs={'pk': artifact.id}), {}, format='json')
        self.assertEqual(response.status_code, 200)
        active_response = self.client.get(reverse('prediction_training:model-active'))
        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(active_response.json()['active_model']['id'], artifact.id)


class PredictionModelGovernanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.provider = Provider.objects.create(name='Demo Provider', slug='demo-provider')
        self.event = Event.objects.create(provider=self.provider, title='Governance Event', slug='governance-event')
        self.market = Market.objects.create(
            provider=self.provider,
            event=self.event,
            title='Model governance market',
            slug='model-governance-market',
            current_market_probability=Decimal('0.5000'),
            source_type='demo',
            resolution_time=timezone.now() + timezone.timedelta(days=7),
        )
        self.dataset = PredictionDatasetRun.objects.create(
            name='manual_compare_dataset',
            status='success',
            label_definition='future_probability_up_24h',
            feature_set_version='prediction_features_v1',
            started_at=timezone.now(),
            finished_at=timezone.now(),
            rows_built=4,
            artifact_path='/tmp/prediction_training_compare_dataset.csv',
        )
        Path(self.dataset.artifact_path).write_text(
            '\\n'.join(
                [
                    'market_id,snapshot_id,captured_at,label,market_probability,recent_snapshot_delta,time_to_resolution_hours,volume_24h,liquidity,narrative_sentiment_probability,narrative_confidence,divergence_score,future_probability',
                    f'{self.market.id},1,2026-01-01T00:00:00+00:00,1,0.45,0.02,20,100,1000,0.61,0.40,0.10,0.51',
                    f'{self.market.id},2,2026-01-01T06:00:00+00:00,0,0.60,-0.02,19,120,1100,0.42,0.30,-0.08,0.53',
                    f'{self.market.id},3,2026-01-01T12:00:00+00:00,1,0.49,0.01,18,130,1200,0.57,0.50,0.12,0.56',
                    f'{self.market.id},4,2026-01-01T18:00:00+00:00,0,0.58,-0.03,17,135,1300,0.39,0.20,-0.11,0.48',
                ]
            ),
            encoding='utf-8',
        )

    def tearDown(self):
        if Path(self.dataset.artifact_path).exists():
            Path(self.dataset.artifact_path).unlink()

    def test_compare_models_persists_run_and_results(self):
        response = self.client.post(
            reverse('prediction_training:compare-models'),
            {
                'baseline_key': 'heuristic_baseline',
                'candidate_key': 'narrative_weighted',
                'profile_slug': 'balanced_model_eval',
                'scope': 'mixed',
                'dataset_run_id': self.dataset.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        run_id = response.json()['id']
        run = ModelComparisonRun.objects.get(id=run_id)
        self.assertEqual(run.status, 'success')
        self.assertEqual(run.results.count(), 2)

    def test_compare_models_fallback_when_artifact_not_available(self):
        response = self.client.post(
            reverse('prediction_training:compare-models'),
            {
                'baseline_key': 'heuristic_baseline',
                'candidate_key': 'artifact:999999',
                'profile_slug': 'balanced_model_eval',
                'dataset_run_id': self.dataset.id,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('not found', response.json()['detail'].lower())

    def test_active_model_recommendation_and_governance_summary_endpoints(self):
        self.client.post(
            reverse('prediction_training:compare-models'),
            {
                'baseline_key': 'heuristic_baseline',
                'candidate_key': 'market_momentum_weighted',
                'profile_slug': 'conservative_model_eval',
                'scope': 'demo_only',
                'dataset_run_id': self.dataset.id,
            },
            format='json',
        )
        recommendation_response = self.client.get(reverse('prediction_training:active-model-recommendation'))
        self.assertEqual(recommendation_response.status_code, 200)
        self.assertIsNotNone(recommendation_response.json().get('recommendation_code'))

        summary_response = self.client.get(reverse('prediction_training:model-governance-summary'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertIn('latest_comparison', summary_response.json())
