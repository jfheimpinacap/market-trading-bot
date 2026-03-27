from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.models import Event, Market, MarketSnapshot, Provider
from apps.memory_retrieval.models import MemoryDocument
from apps.prediction_agent.models import PredictionScore
from apps.prediction_agent.services.features import build_prediction_features
from apps.prediction_agent.services.scoring import score_market_prediction
from apps.research_agent.models import NarrativeItem, NarrativeSource, ResearchCandidate


class PredictionAgentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.provider = Provider.objects.create(name='Kalshi', slug='kalshi')
        self.event = Event.objects.create(provider=self.provider, title='Election event', slug='election-event')
        self.market = Market.objects.create(
            provider=self.provider,
            event=self.event,
            title='Will candidate A win?',
            slug='candidate-a-win',
            current_market_probability=Decimal('0.4300'),
            current_yes_price=Decimal('0.4300'),
            current_no_price=Decimal('0.5700'),
            liquidity=Decimal('100000.00'),
            volume_24h=Decimal('4500.00'),
            volume_total=Decimal('120000.00'),
            resolution_time=timezone.now() + timezone.timedelta(days=10),
            source_type='real_read_only',
        )
        now = timezone.now()
        MarketSnapshot.objects.create(market=self.market, captured_at=now - timezone.timedelta(hours=2), market_probability=Decimal('0.4100'))
        MarketSnapshot.objects.create(market=self.market, captured_at=now - timezone.timedelta(hours=1), market_probability=Decimal('0.4400'))

        source = NarrativeSource.objects.create(name='Demo RSS', slug='demo-rss', source_type='rss', feed_url='https://example.com/feed')
        item = NarrativeItem.objects.create(
            source=source,
            title='Momentum improves for candidate A',
            url='https://example.com/item',
            raw_text='candidate A gains support',
            dedupe_hash='hash-1',
        )
        candidate = ResearchCandidate.objects.create(
            market=self.market,
            narrative_pressure=Decimal('0.7000'),
            sentiment_direction='bullish',
            implied_probability_snapshot=Decimal('0.4300'),
            market_implied_direction='neutral',
            divergence_score=Decimal('0.2500'),
            short_thesis='Narrative supports upside',
            priority=Decimal('0.80'),
        )
        candidate.narrative_items.add(item)
        MemoryDocument.objects.create(
            document_type='prediction_score_snapshot',
            source_app='prediction_agent',
            source_object_id='seed-1',
            title='Execution realism precedent',
            text_content='similar edge degraded in execution realism',
            tags=['negative'],
            structured_summary={'primary_failure_mode': 'execution_drag'},
            embedding=[1.0, 0.0, 0.0],
            embedding_model='mock',
        )

    def test_feature_construction_returns_expected_keys(self):
        result = build_prediction_features(market=self.market)
        self.assertIn('market_probability', result.snapshot)
        self.assertIn('recent_snapshot_delta', result.snapshot)
        self.assertIn('narrative_confidence', result.snapshot)
        self.assertIn('divergence_narrative_vs_market', result.snapshot)

    @patch('apps.memory_retrieval.services.retrieval.embed_text', return_value=[1.0, 0.0, 0.0])
    def test_scoring_market_creates_positive_or_negative_edge(self, _retrieval_embed):
        scored = score_market_prediction(market=self.market, profile_slug='heuristic_baseline', triggered_by='test')
        self.assertIsNotNone(scored.score.id)
        self.assertIn(scored.score.confidence_level, ['low', 'medium', 'high'])
        self.assertTrue(scored.score.rationale)
        self.assertNotEqual(scored.score.system_probability, scored.score.market_probability)
        self.assertIn('precedent_context', scored.score.details)

    def test_api_score_market_endpoint(self):
        response = self.client.post(
            reverse('prediction_agent:score-market'),
            {'market_id': self.market.id, 'profile_slug': 'narrative_weighted', 'triggered_by': 'test_api'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn('system_probability', payload)
        self.assertIn('market_probability', payload)
        self.assertIn('edge', payload)
        self.assertIn('confidence', payload)

    def test_summary_endpoint_and_score_list(self):
        score_market_prediction(market=self.market, profile_slug='heuristic_baseline', triggered_by='test_summary')

        summary_response = self.client.get(reverse('prediction_agent:summary'))
        list_response = self.client.get(reverse('prediction_agent:score-list'))

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(summary_response.json()['total_scores'], 1)
        self.assertGreaterEqual(len(list_response.json()), 1)

    def test_proposal_context_can_read_prediction_score(self):
        score = score_market_prediction(market=self.market, profile_slug='heuristic_baseline', triggered_by='test_context').score
        self.assertTrue(PredictionScore.objects.filter(id=score.id).exists())
