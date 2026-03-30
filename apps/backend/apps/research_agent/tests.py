from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market, MarketStatus
from apps.memory_retrieval.models import MemoryDocument
from apps.research_agent.models import NarrativeAnalysis, NarrativeItem, NarrativeSource, ResearchCandidate
from apps.research_agent.services.clustering import cluster_narratives
from apps.research_agent.services.dedup import deduplicate_narratives
from apps.research_agent.services.filtering import evaluate_structural_filters
from apps.research_agent.services.narrative_linking import link_narrative_signals
from apps.research_agent.services.recommendation import decision_for_candidate
from apps.research_agent.services.scoring import compute_pursue_worthiness
from apps.research_agent.services.run import run_scan_agent
from apps.research_agent.services.scoring import score_cluster
from apps.research_agent.services.source_fetch import ScanRawItem
from apps.research_agent.services.scan import run_research_scan
from apps.research_agent.services.universe_scan import run_universe_scan

RSS_PAYLOAD = {
    'feed': {'title': 'Demo Feed'},
    'entries': [
        {
            'title': 'Election poll shifts toward candidate A',
            'link': 'https://example.com/a',
            'id': 'item-a',
            'published': 'Wed, 25 Mar 2026 10:00:00 +0000',
            'summary': 'Candidate A improves odds in latest poll.',
        },
        {
            'title': 'Fed signals slower rate cuts',
            'link': 'https://example.com/fed',
            'id': 'item-b',
            'published': 'Wed, 25 Mar 2026 11:00:00 +0000',
            'summary': 'Macro narrative shifts risk sentiment.',
        },
    ],
}


class ResearchAgentTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        self.source = NarrativeSource.objects.create(
            name='Demo RSS',
            slug='demo-rss',
            source_type='rss',
            feed_url='https://example.com/feed.xml',
            is_enabled=True,
        )
        self.reddit_source = NarrativeSource.objects.create(
            name='Demo Reddit',
            slug='demo-reddit',
            source_type='reddit',
            is_enabled=True,
            metadata={'subreddit': 'wallstreetbets', 'listing': 'new', 'fetch_limit': 10},
        )
        self.twitter_source = NarrativeSource.objects.create(
            name='Demo Twitter',
            slug='demo-twitter',
            source_type='twitter',
            is_enabled=True,
            metadata={'query': 'fed cuts', 'fetch_limit': 5, 'manual_items': []},
        )

    @patch('apps.research_agent.services.ingest.fetch_rss')
    @patch('apps.research_agent.services.reddit_ingest._fetch_reddit_listing')
    @patch('apps.research_agent.services.twitter_ingest.TwitterSourceAdapter.fetch')
    @patch('apps.memory_retrieval.services.retrieval.embed_text', return_value=[1.0, 0.0, 0.0])
    @patch('apps.research_agent.services.analyze.embed_text', return_value=[0.1, 0.2, 0.3])
    @patch('apps.research_agent.services.analyze.OllamaChatClient.chat_json')
    def test_ingest_dedupe_analyze_link_candidate_and_endpoints(
        self,
        chat_json_mock,
        _embed_mock,
        _retrieval_embed,
        fetch_twitter_mock,
        fetch_reddit_mock,
        fetch_rss_mock,
    ):
        MemoryDocument.objects.create(
            document_type='learning_note',
            source_app='learning_memory',
            source_object_id='r1',
            title='Hype failure precedent',
            text_content='hype-driven narratives had weak follow-through',
            tags=['negative'],
            structured_summary={'primary_failure_mode': 'hype_follow_through_failure'},
            embedding=[1.0, 0.0, 0.0],
            embedding_model='mock',
        )
        fetch_rss_mock.return_value = RSS_PAYLOAD
        fetch_reddit_mock.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'id': 'reddit-a',
                            'title': 'Rate cuts will moon equities this quarter',
                            'selftext': 'Reddit thread expects strong upside in risk assets.',
                            'url': 'https://www.reddit.com/r/wallstreetbets/comments/reddit-a/rate-cuts/',
                            'created_utc': 1774432800,
                            'score': 380,
                            'author': 'demo_author',
                            'permalink': '/r/wallstreetbets/comments/reddit-a/rate-cuts/',
                            'num_comments': 76,
                        }
                    }
                ]
            }
        }
        fetch_twitter_mock.return_value = [
            {
                'id': 'tw-1',
                'text': 'Fed pivot odds rising quickly; macro traders expect risk-on momentum.',
                'author': 'macro_demo',
                'created_at': '2026-03-25T12:00:00Z',
                'url': 'https://x.com/macro_demo/status/tw-1',
                'like_count': 130,
                'retweet_count': 22,
                'reply_count': 8,
            }
        ]
        chat_json_mock.return_value = {
            'summary': 'Narrative suggests improving momentum for a yes outcome in election markets.',
            'sentiment': 'bullish',
            'confidence': 0.81,
            'entities': ['candidate A', 'election'],
            'topics': ['election', 'polling'],
            'market_relevance_score': 0.77,
            'social_signal_strength': 0.69,
            'hype_risk': 0.22,
            'noise_risk': 0.19,
            'market_implication': 'Potential divergence versus stale probability.',
        }

        first_run = run_research_scan()
        second_run = run_research_scan()

        self.assertEqual(first_run.items_created, 4)
        self.assertEqual(first_run.rss_items_created, 2)
        self.assertEqual(first_run.reddit_items_created, 1)
        self.assertEqual(first_run.twitter_items_created, 1)
        self.assertEqual(first_run.social_items_total, 2)
        self.assertGreaterEqual(second_run.items_deduplicated, 4)
        self.assertTrue(NarrativeAnalysis.objects.exists())
        self.assertTrue(NarrativeItem.objects.filter(source__source_type='reddit').exists())
        self.assertTrue(NarrativeItem.objects.filter(source__source_type='twitter').exists())

        sources_response = self.client.get(reverse('research_agent:source-list-create'))
        run_response = self.client.post(reverse('research_agent:run-ingest'), {'run_analysis': True}, format='json')
        full_run_response = self.client.post(reverse('research_agent:run-full-scan'), {}, format='json')
        items_response = self.client.get(reverse('research_agent:item-list'))
        candidates_response = self.client.get(reverse('research_agent:candidate-list'))
        summary_response = self.client.get(reverse('research_agent:summary'))

        self.assertEqual(sources_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(full_run_response.status_code, 200)
        self.assertEqual(items_response.status_code, 200)
        self.assertEqual(candidates_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertGreaterEqual(summary_payload['item_count'], 3)
        self.assertGreaterEqual(summary_payload['reddit_item_count'], 1)
        self.assertGreaterEqual(summary_payload['twitter_item_count'], 1)
        candidate_payload = candidates_response.json()
        if candidate_payload:
            self.assertIn('source_mix', candidate_payload[0])
            self.assertIn('cross_source_agreement', candidate_payload[0]['metadata'])
            self.assertIn('precedent_context', candidate_payload[0]['metadata'])

    def test_universe_scan_filters_and_board_endpoints(self):
        market_open = Market.objects.filter(status=MarketStatus.OPEN).first()
        market_low_liq = Market.objects.exclude(id=market_open.id).first()
        stale_market = Market.objects.exclude(id__in=[market_open.id, market_low_liq.id]).first()

        market_open.liquidity = 200000
        market_open.volume_24h = 35000
        market_open.resolution_time = timezone.now() + timedelta(days=20)
        market_open.updated_at = timezone.now()
        market_open.save(update_fields=['liquidity', 'volume_24h', 'resolution_time', 'updated_at'])

        market_low_liq.liquidity = 100
        market_low_liq.volume_24h = 50
        market_low_liq.status = MarketStatus.CLOSED
        market_low_liq.resolution_time = timezone.now() + timedelta(hours=1)
        market_low_liq.updated_at = timezone.now() - timedelta(days=3)
        market_low_liq.save(update_fields=['liquidity', 'volume_24h', 'status', 'resolution_time', 'updated_at'])

        stale_market.liquidity = 50000
        stale_market.volume_24h = 10000
        stale_market.status = MarketStatus.OPEN
        stale_market.resolution_time = timezone.now() + timedelta(days=10)
        stale_market.updated_at = timezone.now() - timedelta(days=10)
        stale_market.save(update_fields=['liquidity', 'volume_24h', 'status', 'resolution_time', 'updated_at'])

        ResearchCandidate.objects.create(
            market=market_open,
            narrative_pressure='0.8000',
            sentiment_direction='bullish',
            source_mix='mixed',
            priority='75.00',
            metadata={'linked_item_count': 6, 'combined_confidence': 0.8, 'cross_source_agreement': 0.8},
        )

        run = run_universe_scan(filter_profile='balanced_scan')
        self.assertGreater(run.markets_considered, 0)
        self.assertGreaterEqual(run.markets_filtered_out, 1)
        self.assertGreaterEqual(run.markets_shortlisted, 1)
        self.assertTrue(run.details.get('top_exclusion_reasons'))

        run_response = self.client.post(reverse('research_agent:run-universe-scan'), {'filter_profile': 'balanced_scan'}, format='json')
        self.assertEqual(run_response.status_code, 200)

        list_response = self.client.get(reverse('research_agent:universe-scan-list'))
        detail_response = self.client.get(reverse('research_agent:universe-scan-detail', args=[run.id]))
        board_response = self.client.get(reverse('research_agent:board-summary'))
        pursuit_response = self.client.get(reverse('research_agent:pursuit-candidate-list'))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(board_response.status_code, 200)
        self.assertEqual(pursuit_response.status_code, 200)

        pursuit_payload = pursuit_response.json()
        self.assertTrue(any(item['triage_status'] in {'shortlisted', 'watch'} for item in pursuit_payload))
        self.assertTrue(any(item['triage_score'] for item in pursuit_payload))

    def test_scan_agent_dedup_clustering_scoring_and_summary_endpoint(self):
        repeated = ScanRawItem(
            source_type='rss',
            source_slug='demo-rss',
            source_name='Demo RSS',
            title='Fed pivot narrative strengthens',
            url='https://example.com/fed-pivot',
            raw_text='Fed pivot narrative strengthens as traders increase yes bets.',
            snippet='Fed pivot narrative strengthens',
            author='news',
            published_at=timezone.now(),
            metadata={},
        )
        items = [
            repeated,
            repeated,
            ScanRawItem(
                source_type='reddit',
                source_slug='demo-reddit',
                source_name='r/demo',
                title='Fed pivot narrative strengthens this week',
                url='https://reddit.com/r/demo/fed',
                raw_text='Community sees upside and risk-on positioning.',
                snippet='risk-on positioning',
                author='demo',
                published_at=timezone.now(),
                metadata={},
            ),
            ScanRawItem(
                source_type='x',
                source_slug='demo-twitter',
                source_name='Demo X',
                title='Fed pivot odds rising quickly',
                url='https://x.com/demo/status/1',
                raw_text='Odds rising quickly and market still flat.',
                snippet='Odds rising quickly',
                author='macro',
                published_at=timezone.now(),
                metadata={},
            ),
        ]
        dedup = deduplicate_narratives(items)
        self.assertEqual(len(dedup.deduped_items), 3)
        self.assertEqual(len(dedup.ignored_items), 1)

        clusters = cluster_narratives(dedup.deduped_items)
        self.assertGreaterEqual(len(clusters), 1)
        top_cluster = clusters[0]
        score = score_cluster(top_cluster)
        self.assertGreaterEqual(score.novelty_score, 0)
        self.assertGreaterEqual(score.intensity_score, 0)

        with patch('apps.research_agent.services.source_fetch.fetch_parallel_source_items', return_value=(items, {'rss_count': 1, 'reddit_count': 1, 'x_count': 1}, [])):
            run = run_scan_agent()

        self.assertGreaterEqual(run.signal_count, 1)
        self.assertGreaterEqual(run.clustered_count, 1)
        self.assertIsNotNone(run.recommendation_summary)

        summary_response = self.client.get(reverse('scan_agent:summary'))
        signals_response = self.client.get(reverse('scan_agent:signals'))
        clusters_response = self.client.get(reverse('scan_agent:clusters'))
        recommendations_response = self.client.get(reverse('scan_agent:recommendations'))
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(signals_response.status_code, 200)
        self.assertEqual(clusters_response.status_code, 200)
        self.assertEqual(recommendations_response.status_code, 200)
        self.assertIn('latest_run', summary_response.json())


class ResearchUniverseHardeningTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()

    def test_filtering_scoring_linking_recommendation_and_summary_endpoint(self):
        market = Market.objects.filter(status=MarketStatus.OPEN).first()
        market.liquidity = 25000
        market.volume_24h = 8200
        market.resolution_time = timezone.now() + timedelta(days=18)
        market.current_market_probability = '0.62'
        market.current_yes_price = '0.61'
        market.save(update_fields=['liquidity', 'volume_24h', 'resolution_time', 'current_market_probability', 'current_yes_price'])

        run = run_scan_agent()
        signal = run.signals.first()
        if signal:
            signal.linked_market = market
            signal.save(update_fields=['linked_market'])

        structural = evaluate_structural_filters(market=market, now=timezone.now())
        self.assertTrue(structural.open_ok)
        self.assertGreaterEqual(structural.liquidity_score, 0)

        narrative = link_narrative_signals(market=market)
        score = compute_pursue_worthiness(structural=structural, narrative_context=narrative, precedent_context={'caution_weight': '0'})
        self.assertGreaterEqual(score, 0)

        run_response = self.client.post('/api/research-agent/run-universe-scan/', {}, format='json')
        self.assertEqual(run_response.status_code, 200)

        candidates = self.client.get('/api/research-agent/candidates/')
        decisions = self.client.get('/api/research-agent/triage-decisions/')
        recommendations = self.client.get('/api/research-agent/recommendations/')
        summary = self.client.get('/api/research-agent/universe-summary/')

        self.assertEqual(candidates.status_code, 200)
        self.assertEqual(decisions.status_code, 200)
        self.assertEqual(recommendations.status_code, 200)
        self.assertEqual(summary.status_code, 200)
        self.assertIn('totals', summary.json())

        candidate_payload = candidates.json()
        self.assertTrue(len(candidate_payload) > 0)
        decision_payload = decisions.json()[0]
        self.assertIn(decision_payload['decision_type'], {'send_to_prediction', 'keep_on_watchlist', 'ignore_market', 'require_manual_review', 'research_followup'})

        # recommendation helper maps status cleanly
        class _Candidate:
            status = 'watchlist'
            reason_codes = []
            pursue_worthiness_score = '0.55'

        mapped = decision_for_candidate(candidate=_Candidate())
        self.assertEqual(mapped['decision_type'], 'keep_on_watchlist')
