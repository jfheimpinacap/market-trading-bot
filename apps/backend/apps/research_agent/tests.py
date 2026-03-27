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
