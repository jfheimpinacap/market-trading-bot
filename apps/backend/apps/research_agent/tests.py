from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.research_agent.models import NarrativeAnalysis, NarrativeItem, NarrativeSource
from apps.research_agent.services.scan import run_research_scan

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

    @patch('apps.research_agent.services.ingest.fetch_rss')
    @patch('apps.research_agent.services.reddit_ingest._fetch_reddit_listing')
    @patch('apps.research_agent.services.analyze.embed_text', return_value=[0.1, 0.2, 0.3])
    @patch('apps.research_agent.services.analyze.OllamaChatClient.chat_json')
    def test_ingest_dedupe_analyze_link_candidate_and_endpoints(self, chat_json_mock, _embed_mock, fetch_reddit_mock, fetch_rss_mock):
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

        self.assertEqual(first_run.items_created, 3)
        self.assertEqual(first_run.rss_items_created, 2)
        self.assertEqual(first_run.reddit_items_created, 1)
        self.assertGreaterEqual(second_run.items_deduplicated, 3)
        self.assertTrue(NarrativeAnalysis.objects.exists())
        self.assertTrue(NarrativeItem.objects.filter(source__source_type='reddit').exists())

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
        candidate_payload = candidates_response.json()
        if candidate_payload:
            self.assertIn('source_mix', candidate_payload[0])
