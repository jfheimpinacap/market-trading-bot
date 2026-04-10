from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.markets.demo_data import seed_demo_markets
from apps.markets.models import Market, MarketStatus
from apps.memory_retrieval.models import MemoryDocument
from apps.research_agent.models import (
    MarketResearchCandidate,
    MarketUniverseRun,
    NarrativeAnalysis,
    NarrativeConsensusState,
    NarrativeItem,
    NarrativeSignalStatus,
    NarrativeSource,
    ResearchPursuitScoreStatus,
    ResearchCandidate,
    ResearchHandoffStatus,
)
from apps.research_agent.services.pursuit_scoring.run import run_pursuit_review
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
from apps.research_agent.services.intelligence_handoff.run import run_consensus_review

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

        with patch('apps.research_agent.services.run.fetch_parallel_source_items', return_value=(items, {'rss_count': 1, 'reddit_count': 1, 'x_count': 1}, [])):
            run = run_scan_agent()

        self.assertGreaterEqual(run.signal_count, 0)
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


class ScanAgentDiagnosticsFallbackTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()

    def test_empty_real_scan_has_explicit_diagnostics(self):
        with override_settings(ENVIRONMENT='production', SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED=False):
            run = run_scan_agent()

        diagnostics = (run.metadata or {}).get('scan_diagnostics') or {}
        self.assertEqual(run.signal_count, 0)
        self.assertIn('NO_RSS_SOURCE_CONFIGURED', diagnostics.get('zero_signal_reason_codes', []))
        self.assertIn('NO_REDDIT_SOURCE_CONFIGURED', diagnostics.get('zero_signal_reason_codes', []))
        self.assertIn('NO_X_SOURCE_CONFIGURED', diagnostics.get('zero_signal_reason_codes', []))
        self.assertIn('ALL_SOURCES_EMPTY', diagnostics.get('zero_signal_reason_codes', []))
        self.assertTrue(diagnostics.get('diagnostic_summary'))

    def test_demo_mode_uses_fallback_when_enabled_and_no_real_sources(self):
        with override_settings(ENVIRONMENT='local', SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED=True):
            run = run_scan_agent()

        diagnostics = (run.metadata or {}).get('scan_diagnostics') or {}
        self.assertGreater(run.signal_count, 0)
        self.assertGreater(run.clustered_count, 0)
        self.assertIn('DEMO_FALLBACK_USED', diagnostics.get('zero_signal_reason_codes', []))
        self.assertTrue((run.metadata or {}).get('demo_fallback_used'))

        signal = run.signals.order_by('-total_signal_score', '-id').first()
        self.assertIsNotNone(signal)
        self.assertEqual(signal.status, NarrativeSignalStatus.SHORTLISTED)
        self.assertTrue(signal.metadata.get('is_demo'))
        self.assertTrue(signal.metadata.get('is_synthetic'))
        self.assertTrue(signal.metadata.get('is_fallback'))
        self.assertIn('DEMO_SYNTHETIC_FALLBACK', signal.reason_codes)

    def test_demo_mode_disabled_fallback_stays_zero_with_reason_code(self):
        with override_settings(ENVIRONMENT='local', SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED=False):
            run = run_scan_agent()

        diagnostics = (run.metadata or {}).get('scan_diagnostics') or {}
        self.assertEqual(run.signal_count, 0)
        self.assertIn('DEMO_FALLBACK_DISABLED', diagnostics.get('zero_signal_reason_codes', []))
        self.assertFalse((run.metadata or {}).get('demo_fallback_used'))

    @patch('apps.research_agent.services.run.fetch_parallel_source_items')
    def test_real_sources_take_precedence_and_do_not_mark_fallback(self, mock_fetch):
        item = ScanRawItem(
            source_type='rss',
            source_slug='real-rss',
            source_name='Real RSS',
            title='rates macro outlook upside',
            url='https://example.com/real-source',
            raw_text='Macro upside narrative with rise in conviction.',
            snippet='upside rise conviction',
            author='wire',
            published_at=timezone.now(),
            metadata={},
        )
        mock_fetch.return_value = ([item], {'rss_count': 1, 'reddit_count': 0, 'x_count': 0}, [])

        with override_settings(ENVIRONMENT='local', SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED=True):
            run = run_scan_agent()

        diagnostics = (run.metadata or {}).get('scan_diagnostics') or {}
        self.assertGreater(run.raw_item_count, 0)
        self.assertFalse((run.metadata or {}).get('demo_fallback_used'))
        self.assertNotIn('DEMO_FALLBACK_USED', diagnostics.get('zero_signal_reason_codes', []))

    def test_summary_endpoint_exposes_diagnostics_and_reason_codes(self):
        with override_settings(ENVIRONMENT='local', SCAN_DEMO_NARRATIVE_FALLBACK_ENABLED=False):
            run = run_scan_agent()

        self.assertIsNotNone(run)
        response = self.client.get(reverse('scan_agent:summary'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        latest = payload.get('latest_run') or {}
        diagnostics = (latest.get('metadata') or {}).get('scan_diagnostics') or {}
        self.assertIn('zero_signal_reason_codes', diagnostics)
        self.assertTrue(diagnostics.get('diagnostic_summary'))


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


class ResearchPursuitHardeningTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()
        run_scan_agent()
        run_consensus_review(triggered_by='test')
        self.universe_run = MarketUniverseRun.objects.create(started_at=timezone.now(), completed_at=timezone.now())

    def _seed_candidate(self, market):
        MarketResearchCandidate.objects.update_or_create(
            universe_run=self.universe_run,
            linked_market=market,
            defaults={
                'market_title': market.title,
                'market_provider': market.provider.slug,
                'category': market.category,
                'time_to_resolution_hours': 24,
                'liquidity_score': '0.7000',
                'volume_score': '0.7000',
                'freshness_score': '0.7000',
                'market_quality_score': '0.7000',
                'narrative_support_score': '0.7000',
                'divergence_score': '0.6000',
                'pursue_worthiness_score': '0.7000',
                'status': 'shortlist',
                'rationale': 'test candidate',
            },
        )

    def test_structurally_strong_market_is_prediction_ready(self):
        market = Market.objects.filter(status=MarketStatus.OPEN).first()
        market.liquidity = 50000
        market.volume_24h = 25000
        market.updated_at = timezone.now()
        market.resolution_time = timezone.now() + timedelta(days=10)
        market.save(update_fields=['liquidity', 'volume_24h', 'updated_at', 'resolution_time'])
        self._seed_candidate(market)

        run = run_pursuit_review(market_limit=50, triggered_by='test')
        score = run.scores.filter(linked_market=market).order_by('-id').first()
        self.assertIsNotNone(score)
        self.assertEqual(score.score_status, ResearchPursuitScoreStatus.READY_FOR_PREDICTION)

    def test_low_liquidity_or_stale_market_gets_deferred_or_blocked(self):
        market = Market.objects.filter(status=MarketStatus.OPEN).first()
        market.liquidity = 50
        market.volume_24h = 80
        market.updated_at = timezone.now() - timedelta(days=9)
        market.resolution_time = timezone.now() + timedelta(days=7)
        market.save(update_fields=['liquidity', 'volume_24h', 'updated_at', 'resolution_time'])
        self._seed_candidate(market)

        run = run_pursuit_review(market_limit=50, triggered_by='test')
        score = run.scores.filter(linked_market=market).order_by('-id').first()
        self.assertIn(score.score_status, {ResearchPursuitScoreStatus.DEFER, ResearchPursuitScoreStatus.BLOCK})

    def test_high_divergence_increases_priority_bucket(self):
        run = run_pursuit_review(market_limit=50, triggered_by='test')
        high_divergence_score = run.scores.filter(linked_assessment__linked_divergence_record__divergence_state='high_divergence').first()
        if high_divergence_score:
            self.assertIn(high_divergence_score.priority_bucket, {'critical', 'high', 'medium'})

    def test_poor_time_window_defers_handoff(self):
        market = Market.objects.filter(status=MarketStatus.OPEN).first()
        market.liquidity = 40000
        market.volume_24h = 15000
        market.resolution_time = timezone.now() + timedelta(hours=3)
        market.updated_at = timezone.now()
        market.save(update_fields=['liquidity', 'volume_24h', 'resolution_time', 'updated_at'])
        self._seed_candidate(market)

        run = run_pursuit_review(market_limit=50, triggered_by='test')
        handoff = run.prediction_handoffs.filter(linked_market=market).order_by('-id').first()
        self.assertIn(handoff.handoff_status, {'deferred', 'blocked'})

    def test_pursuit_summary_endpoint(self):
        self.client.post('/api/research-agent/run-pursuit-review/', {}, format='json')
        response = self.client.get('/api/research-agent/pursuit-summary/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('totals', response.json())

        # recommendation helper maps status cleanly
        class _Candidate:
            status = 'watchlist'
            reason_codes = []
            pursue_worthiness_score = '0.55'

        mapped = decision_for_candidate(candidate=_Candidate())
        self.assertEqual(mapped['decision_type'], 'keep_on_watchlist')


class ScanConsensusHandoffTests(TestCase):
    def setUp(self):
        seed_demo_markets()
        self.client = APIClient()

    def test_consensus_divergence_priority_and_summary_endpoints(self):
        market = Market.objects.filter(status=MarketStatus.OPEN).first()
        market.current_market_probability = '0.20'
        market.save(update_fields=['current_market_probability'])

        items = [
            ScanRawItem(source_type='rss', source_slug='r1', source_name='rss', title='Topic A', url='https://a', raw_text='bullish yes', snippet='bullish', author='a', published_at=timezone.now(), metadata={}),
            ScanRawItem(source_type='reddit', source_slug='r2', source_name='reddit', title='Topic A strong', url='https://b', raw_text='bullish yes momentum', snippet='bullish', author='b', published_at=timezone.now(), metadata={}),
            ScanRawItem(source_type='x', source_slug='r3', source_name='x', title='Topic A debate', url='https://c', raw_text='bearish yes unwind', snippet='bearish', author='c', published_at=timezone.now(), metadata={}),
        ]
        with patch('apps.research_agent.services.run.fetch_parallel_source_items', return_value=(items, {'rss_count': 1, 'reddit_count': 1, 'x_count': 1}, [])):
            scan_run = run_scan_agent()

        first_signal = scan_run.signals.first()
        if first_signal:
            first_signal.linked_market = market
            first_signal.save(update_fields=['linked_market'])
        run = run_consensus_review()

        self.assertGreaterEqual(run.considered_signal_count, 1)
        self.assertGreaterEqual(run.consensus_detected_count, 0)

        records_response = self.client.get(reverse('scan_agent:consensus-records'))
        divergence_response = self.client.get(reverse('scan_agent:market-divergence-records'))
        priorities_response = self.client.get(reverse('scan_agent:research-handoff-priorities'))
        recommendations_response = self.client.get(reverse('scan_agent:consensus-recommendations'))
        summary_response = self.client.get(reverse('scan_agent:consensus-summary'))
        run_response = self.client.post(reverse('scan_agent:run-consensus-review'), {}, format='json')

        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(divergence_response.status_code, 200)
        self.assertEqual(priorities_response.status_code, 200)
        self.assertEqual(recommendations_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(run_response.status_code, 200)
        self.assertIn('signals_considered', summary_response.json())
        self.assertTrue(
            any(item['handoff_status'] in {ResearchHandoffStatus.READY_FOR_RESEARCH, 'deferred', 'blocked', 'watchlist'} for item in priorities_response.json())
        )
        self.assertTrue(any(item['consensus_state'] in {NarrativeConsensusState.STRONG_CONSENSUS, 'conflicted', 'weak_consensus', 'mixed', 'insufficient_signal'} for item in records_response.json()))


class MarketContextLinkingTests(TestCase):
    def test_infer_target_market_returns_none_for_ambiguous_top_candidates(self):
        from apps.markets.models import Provider
        from apps.research_agent.services.market_context import infer_target_market

        provider = Provider.objects.create(name='Ambiguous Link Provider', slug='amb-link-provider')
        Market.objects.create(provider=provider, title='Election Senate Winner 2026', slug='amb-election-2026', is_active=True, status=MarketStatus.OPEN)
        Market.objects.create(provider=provider, title='Election Senate Winner 2027', slug='amb-election-2027', is_active=True, status=MarketStatus.OPEN)

        resolved = infer_target_market('Election Senate Winner')
        self.assertIsNone(resolved)

    def test_infer_target_market_resolves_unique_candidate(self):
        from apps.markets.models import Provider
        from apps.research_agent.services.market_context import infer_target_market

        provider = Provider.objects.create(name='Resolved Link Provider', slug='resolved-link-provider')
        expected = Market.objects.create(provider=provider, title='Fed rate cut June decision', slug='fed-cut-june', is_active=True, status=MarketStatus.OPEN)
        Market.objects.create(provider=provider, title='World Cup winner 2026', slug='world-cup-winner-2026', is_active=True, status=MarketStatus.OPEN)

        resolved = infer_target_market('Fed rate cut June decision')
        self.assertEqual(getattr(resolved, 'id', None), expected.id)
