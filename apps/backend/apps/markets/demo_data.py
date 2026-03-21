from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .models import (
    Event,
    EventStatus,
    Market,
    MarketRule,
    MarketSnapshot,
    MarketStatus,
    MarketType,
    OutcomeType,
    Provider,
    RuleSourceType,
)

SEED_GENERATED_AT = timezone.datetime(2026, 3, 20, 15, 0, tzinfo=dt_timezone.utc)


@dataclass(frozen=True)
class SnapshotPoint:
    hours_offset: int
    probability: str
    liquidity: str
    volume: str
    volume_24h: str
    open_interest: str
    spread_cents: str


PROVIDERS: list[dict[str, Any]] = [
    {
        'slug': 'kalshi',
        'name': 'Kalshi Demo',
        'description': 'Local demo provider catalog for binary macro, politics, and sports markets.',
        'base_url': 'https://demo.local/providers/kalshi',
        'api_base_url': 'https://demo.local/api/providers/kalshi',
        'notes': 'Demo-only catalog. No external API integration is configured.',
        'is_active': True,
    },
    {
        'slug': 'polymarket',
        'name': 'Polymarket Demo',
        'description': 'Local demo provider catalog for technology, politics, and economic test markets.',
        'base_url': 'https://demo.local/providers/polymarket',
        'api_base_url': 'https://demo.local/api/providers/polymarket',
        'notes': 'Demo-only catalog. Provider-agnostic backend fixture for frontend work.',
        'is_active': True,
    },
]


EVENTS: list[dict[str, Any]] = [
    {
        'provider_slug': 'kalshi',
        'provider_event_id': 'kalshi-demo-election-2028',
        'title': 'US Presidential Election 2028 Demo',
        'category': 'politics',
        'status': EventStatus.OPEN,
        'description': 'Fictional election event used to test catalog views and grouped markets.',
        'open_time': timezone.datetime(2026, 1, 10, 12, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2028, 11, 5, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2028, 11, 6, 18, 0, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'politics'},
    },
    {
        'provider_slug': 'kalshi',
        'provider_event_id': 'kalshi-demo-cpi-june-2026',
        'title': 'US CPI Release June 2026 Demo',
        'category': 'economics',
        'status': EventStatus.OPEN,
        'description': 'Macro demo event around a CPI print with multiple probability scenarios.',
        'open_time': timezone.datetime(2026, 2, 1, 13, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 6, 10, 12, 25, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 6, 10, 13, 30, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'macro'},
    },
    {
        'provider_slug': 'kalshi',
        'provider_event_id': 'kalshi-demo-football-final-2026',
        'title': 'Continental Football Final 2026 Demo',
        'category': 'sports',
        'status': EventStatus.UPCOMING,
        'description': 'Sports event for local UI testing with an upcoming match and a live-style market.',
        'open_time': timezone.datetime(2026, 4, 20, 16, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 7, 18, 18, 45, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 7, 18, 21, 30, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'sports'},
    },
    {
        'provider_slug': 'polymarket',
        'provider_event_id': 'pm-demo-ai-launch-2026',
        'title': 'AI Platform Launch Window 2026 Demo',
        'category': 'technology',
        'status': EventStatus.OPEN,
        'description': 'Technology launch demo event for product release and adoption-style markets.',
        'open_time': timezone.datetime(2026, 1, 15, 14, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 9, 30, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 10, 1, 15, 0, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'technology'},
    },
    {
        'provider_slug': 'polymarket',
        'provider_event_id': 'pm-demo-rate-cut-2026',
        'title': 'Federal Reserve Rate Path 2026 Demo',
        'category': 'economics',
        'status': EventStatus.OPEN,
        'description': 'Interest-rate themed event for local dashboards and filter testing.',
        'open_time': timezone.datetime(2026, 1, 8, 15, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 12, 16, 19, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 12, 16, 21, 0, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'rates'},
    },
    {
        'provider_slug': 'polymarket',
        'provider_event_id': 'pm-demo-chip-export-2025',
        'title': 'Chip Export Policy 2025 Demo',
        'category': 'geopolitics',
        'status': EventStatus.RESOLVED,
        'description': 'Resolved policy event with closed markets and historical snapshots.',
        'open_time': timezone.datetime(2025, 7, 1, 12, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2025, 11, 5, 17, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2025, 11, 6, 15, 0, tzinfo=dt_timezone.utc),
        'metadata': {'demo': True, 'theme': 'policy'},
    },
]


MARKETS: list[dict[str, Any]] = [
    {
        'provider_slug': 'kalshi',
        'event_title': 'US Presidential Election 2028 Demo',
        'provider_market_id': 'k-demo-2028-candidate-a',
        'ticker': 'DEMO-POL-2028-A',
        'title': 'Will Candidate A win the 2028 election?',
        'category': 'politics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo election desk',
        'short_rules': 'Resolves Yes if Candidate A is certified as the winner of the 2028 election.',
        'url': 'https://demo.local/markets/k-demo-2028-candidate-a',
        'open_time': timezone.datetime(2026, 1, 10, 12, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2028, 11, 5, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2028, 11, 6, 18, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.5400',
        'liquidity': '285000.0000',
        'volume_24h': '18250.0000',
        'volume_total': '512400.0000',
        'spread_bps': 180,
        'metadata': {'demo': True, 'theme': 'headline'},
        'snapshots': [
            SnapshotPoint(-30, '0.4800', '245000', '450200', '12100', '95000', '0.0180'),
            SnapshotPoint(-24, '0.4950', '252500', '458400', '12840', '97000', '0.0160'),
            SnapshotPoint(-18, '0.5075', '261000', '466000', '13420', '99500', '0.0150'),
            SnapshotPoint(-12, '0.5230', '270000', '478300', '14980', '101200', '0.0140'),
            SnapshotPoint(-6, '0.5310', '279500', '494200', '16320', '103500', '0.0130'),
            SnapshotPoint(0, '0.5400', '285000', '512400', '18250', '105400', '0.0120'),
        ],
        'rules': [
            {
                'source_type': RuleSourceType.PROVIDER,
                'rule_text': 'Certification by the designated federal authority determines the final outcome.',
                'resolution_criteria': 'If Candidate A is officially certified as the winner, the market resolves Yes.',
            },
            {
                'source_type': RuleSourceType.MANUAL,
                'rule_text': 'This is a fictional market used for local development and UI testing only.',
                'resolution_criteria': 'No real trading or provider settlement applies.',
            },
        ],
    },
    {
        'provider_slug': 'kalshi',
        'event_title': 'US Presidential Election 2028 Demo',
        'provider_market_id': 'k-demo-2028-turnout',
        'ticker': 'DEMO-POL-2028-TURNOUT',
        'title': 'Will voter turnout exceed 64% in the 2028 election?',
        'category': 'politics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo elections reference board',
        'short_rules': 'Resolves Yes if national turnout is reported above 64.0%.',
        'url': 'https://demo.local/markets/k-demo-2028-turnout',
        'open_time': timezone.datetime(2026, 1, 12, 13, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2028, 11, 5, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2028, 11, 7, 18, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.4100',
        'liquidity': '162000.0000',
        'volume_24h': '9340.0000',
        'volume_total': '214500.0000',
        'spread_bps': 220,
        'metadata': {'demo': True, 'theme': 'turnout'},
        'snapshots': [
            SnapshotPoint(-30, '0.3650', '132000', '170000', '6500', '64000', '0.0220'),
            SnapshotPoint(-24, '0.3720', '136500', '176100', '7010', '65800', '0.0200'),
            SnapshotPoint(-18, '0.3850', '142500', '182400', '7480', '67000', '0.0190'),
            SnapshotPoint(-12, '0.3960', '149800', '191000', '8120', '68800', '0.0180'),
            SnapshotPoint(-6, '0.4030', '156900', '203100', '8790', '70200', '0.0170'),
            SnapshotPoint(0, '0.4100', '162000', '214500', '9340', '71800', '0.0160'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'kalshi',
        'event_title': 'US CPI Release June 2026 Demo',
        'provider_market_id': 'k-demo-cpi-over-33',
        'ticker': 'DEMO-CPI-33',
        'title': 'Will inflation be above 3.3% by June 2026?',
        'category': 'economics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo BLS feed',
        'short_rules': 'Resolves Yes if the reference CPI release prints above 3.3%.',
        'url': 'https://demo.local/markets/k-demo-cpi-over-33',
        'open_time': timezone.datetime(2026, 2, 1, 13, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 6, 10, 12, 25, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 6, 10, 13, 30, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.6200',
        'liquidity': '98000.0000',
        'volume_24h': '11450.0000',
        'volume_total': '168200.0000',
        'spread_bps': 140,
        'metadata': {'demo': True, 'theme': 'macro'},
        'snapshots': [
            SnapshotPoint(-30, '0.5750', '85000', '129000', '7200', '40200', '0.0140'),
            SnapshotPoint(-24, '0.5840', '87200', '135800', '7810', '41300', '0.0130'),
            SnapshotPoint(-18, '0.5960', '90100', '143900', '8560', '42450', '0.0120'),
            SnapshotPoint(-12, '0.6050', '93100', '151700', '9420', '43320', '0.0110'),
            SnapshotPoint(-6, '0.6120', '95800', '160100', '10420', '44120', '0.0100'),
            SnapshotPoint(0, '0.6200', '98000', '168200', '11450', '45000', '0.0090'),
        ],
        'rules': [
            {
                'source_type': RuleSourceType.PROVIDER,
                'rule_text': 'Use the scheduled reference inflation release for June 2026 as the source of truth.',
                'resolution_criteria': 'Prints strictly above 3.3% resolve Yes; 3.3% or lower resolves No.',
            },
        ],
    },
    {
        'provider_slug': 'kalshi',
        'event_title': 'US CPI Release June 2026 Demo',
        'provider_market_id': 'k-demo-cpi-core-over-30',
        'ticker': 'DEMO-CORE-CPI-30',
        'title': 'Will core inflation stay above 3.0% in June 2026?',
        'category': 'economics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.PAUSED,
        'is_active': False,
        'resolution_source': 'Demo macro desk',
        'short_rules': 'Temporarily paused for local UI testing of non-active markets.',
        'url': 'https://demo.local/markets/k-demo-cpi-core-over-30',
        'open_time': timezone.datetime(2026, 2, 1, 13, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 6, 10, 12, 25, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 6, 10, 13, 30, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.4700',
        'liquidity': '74100.0000',
        'volume_24h': '2800.0000',
        'volume_total': '94600.0000',
        'spread_bps': 360,
        'metadata': {'demo': True, 'theme': 'paused-market'},
        'snapshots': [
            SnapshotPoint(-30, '0.5050', '70000', '81200', '2600', '32100', '0.0320'),
            SnapshotPoint(-24, '0.4960', '71100', '83000', '2500', '31950', '0.0330'),
            SnapshotPoint(-18, '0.4890', '72000', '85200', '2450', '31880', '0.0340'),
            SnapshotPoint(-12, '0.4810', '73000', '87550', '2380', '31700', '0.0350'),
            SnapshotPoint(-6, '0.4750', '73600', '90300', '2300', '31540', '0.0360'),
            SnapshotPoint(0, '0.4700', '74100', '94600', '2800', '31400', '0.0370'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'kalshi',
        'event_title': 'Continental Football Final 2026 Demo',
        'provider_market_id': 'k-demo-final-team-z',
        'ticker': 'DEMO-SPORT-TEAMZ',
        'title': 'Will Team Z win the final?',
        'category': 'sports',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo sports wire',
        'short_rules': 'Resolves Yes if Team Z is the official winner after standard competition rules.',
        'url': 'https://demo.local/markets/k-demo-final-team-z',
        'open_time': timezone.datetime(2026, 4, 20, 16, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 7, 18, 18, 45, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 7, 18, 21, 30, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.5800',
        'liquidity': '143500.0000',
        'volume_24h': '12600.0000',
        'volume_total': '143500.0000',
        'spread_bps': 170,
        'metadata': {'demo': True, 'theme': 'sports-final'},
        'snapshots': [
            SnapshotPoint(-30, '0.5200', '118000', '98000', '6400', '52000', '0.0180'),
            SnapshotPoint(-24, '0.5350', '122000', '105500', '7300', '53200', '0.0170'),
            SnapshotPoint(-18, '0.5480', '126500', '114000', '8500', '54500', '0.0160'),
            SnapshotPoint(-12, '0.5610', '132000', '123100', '9720', '55600', '0.0150'),
            SnapshotPoint(-6, '0.5700', '138000', '133800', '11110', '56600', '0.0140'),
            SnapshotPoint(0, '0.5800', '143500', '143500', '12600', '57500', '0.0130'),
        ],
        'rules': [
            {
                'source_type': RuleSourceType.PROVIDER,
                'rule_text': 'Extra time and penalty shootouts count toward the official winner.',
                'resolution_criteria': 'If Team Z lifts the trophy, resolve Yes.',
            },
        ],
    },
    {
        'provider_slug': 'kalshi',
        'event_title': 'Continental Football Final 2026 Demo',
        'provider_market_id': 'k-demo-final-over-25',
        'ticker': 'DEMO-SPORT-O25',
        'title': 'Will the final have over 2.5 total goals?',
        'category': 'sports',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.CLOSED,
        'is_active': False,
        'resolution_source': 'Demo sports wire',
        'short_rules': 'Market is closed to simulate a pre-resolution final state for the frontend.',
        'url': 'https://demo.local/markets/k-demo-final-over-25',
        'open_time': timezone.datetime(2026, 4, 20, 16, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 7, 18, 18, 45, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 7, 18, 21, 30, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.5100',
        'liquidity': '118900.0000',
        'volume_24h': '14800.0000',
        'volume_total': '176400.0000',
        'spread_bps': 95,
        'metadata': {'demo': True, 'theme': 'closing-market'},
        'snapshots': [
            SnapshotPoint(-30, '0.4600', '98000', '122000', '9100', '48200', '0.0140'),
            SnapshotPoint(-24, '0.4720', '101500', '131100', '10300', '49100', '0.0130'),
            SnapshotPoint(-18, '0.4850', '105400', '141300', '11500', '50000', '0.0120'),
            SnapshotPoint(-12, '0.4970', '110200', '151700', '12620', '51000', '0.0110'),
            SnapshotPoint(-6, '0.5030', '114700', '163800', '13800', '51800', '0.0100'),
            SnapshotPoint(0, '0.5100', '118900', '176400', '14800', '52500', '0.0090'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'AI Platform Launch Window 2026 Demo',
        'provider_market_id': 'pm-demo-ai-product-launch',
        'ticker': 'DEMO-TECH-LAUNCH',
        'title': 'Will Company X launch product Y before September 30, 2026?',
        'category': 'technology',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo technology release tracker',
        'short_rules': 'Resolves Yes if Product Y is publicly launched before the deadline.',
        'url': 'https://demo.local/markets/pm-demo-ai-product-launch',
        'open_time': timezone.datetime(2026, 1, 15, 14, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 9, 30, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 10, 1, 15, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.6700',
        'liquidity': '205600.0000',
        'volume_24h': '22100.0000',
        'volume_total': '391200.0000',
        'spread_bps': 125,
        'metadata': {'demo': True, 'theme': 'launch'},
        'snapshots': [
            SnapshotPoint(-30, '0.5900', '170000', '305000', '14300', '81100', '0.0140'),
            SnapshotPoint(-24, '0.6080', '177200', '318000', '15800', '82500', '0.0130'),
            SnapshotPoint(-18, '0.6250', '184500', '334500', '17600', '84000', '0.0120'),
            SnapshotPoint(-12, '0.6410', '191700', '351900', '19100', '85600', '0.0110'),
            SnapshotPoint(-6, '0.6550', '198800', '370800', '20800', '87100', '0.0100'),
            SnapshotPoint(0, '0.6700', '205600', '391200', '22100', '88800', '0.0090'),
        ],
        'rules': [
            {
                'source_type': RuleSourceType.PROVIDER,
                'rule_text': 'A public general-availability launch announcement is sufficient for resolution.',
                'resolution_criteria': 'Private beta access alone does not count as a launch.',
            },
        ],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'AI Platform Launch Window 2026 Demo',
        'provider_market_id': 'pm-demo-ai-users',
        'ticker': 'DEMO-TECH-USERS',
        'title': 'Will Product Y reach 10 million users by December 2026?',
        'category': 'technology',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo analytics board',
        'short_rules': 'Resolves Yes if public company reporting shows at least 10 million users in 2026.',
        'url': 'https://demo.local/markets/pm-demo-ai-users',
        'open_time': timezone.datetime(2026, 2, 1, 14, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 12, 31, 23, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2027, 1, 15, 15, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.3600',
        'liquidity': '129400.0000',
        'volume_24h': '9800.0000',
        'volume_total': '208600.0000',
        'spread_bps': 240,
        'metadata': {'demo': True, 'theme': 'adoption'},
        'snapshots': [
            SnapshotPoint(-30, '0.3200', '111000', '160200', '7100', '60300', '0.0230'),
            SnapshotPoint(-24, '0.3290', '114500', '168000', '7600', '61100', '0.0220'),
            SnapshotPoint(-18, '0.3370', '118000', '176200', '8100', '61900', '0.0210'),
            SnapshotPoint(-12, '0.3450', '121700', '186000', '8720', '62600', '0.0200'),
            SnapshotPoint(-6, '0.3520', '125400', '196500', '9280', '63200', '0.0190'),
            SnapshotPoint(0, '0.3600', '129400', '208600', '9800', '64000', '0.0180'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'Federal Reserve Rate Path 2026 Demo',
        'provider_market_id': 'pm-demo-fed-cut-2',
        'ticker': 'DEMO-RATES-2CUTS',
        'title': 'Will the Fed deliver at least 2 rate cuts in 2026?',
        'category': 'economics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo FOMC schedule tracker',
        'short_rules': 'Uses the total number of target-range reductions completed in 2026.',
        'url': 'https://demo.local/markets/pm-demo-fed-cut-2',
        'open_time': timezone.datetime(2026, 1, 8, 15, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 12, 16, 19, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 12, 16, 21, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.4400',
        'liquidity': '158300.0000',
        'volume_24h': '11400.0000',
        'volume_total': '248800.0000',
        'spread_bps': 160,
        'metadata': {'demo': True, 'theme': 'rates'},
        'snapshots': [
            SnapshotPoint(-30, '0.4000', '132000', '193000', '7700', '72000', '0.0170'),
            SnapshotPoint(-24, '0.4080', '136200', '201500', '8340', '73100', '0.0160'),
            SnapshotPoint(-18, '0.4170', '141100', '210800', '8960', '74200', '0.0150'),
            SnapshotPoint(-12, '0.4250', '146400', '221900', '9790', '75100', '0.0140'),
            SnapshotPoint(-6, '0.4330', '152400', '234700', '10620', '76100', '0.0130'),
            SnapshotPoint(0, '0.4400', '158300', '248800', '11400', '77000', '0.0120'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'Federal Reserve Rate Path 2026 Demo',
        'provider_market_id': 'pm-demo-fed-upper-bound',
        'ticker': 'DEMO-RATES-UPPER',
        'title': 'Will the policy rate end 2026 above 4.00%?',
        'category': 'economics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.OPEN,
        'is_active': True,
        'resolution_source': 'Demo FOMC schedule tracker',
        'short_rules': 'Resolves based on the upper bound of the target range after the final 2026 meeting.',
        'url': 'https://demo.local/markets/pm-demo-fed-upper-bound',
        'open_time': timezone.datetime(2026, 1, 8, 15, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2026, 12, 16, 19, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2026, 12, 16, 21, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.5200',
        'liquidity': '147100.0000',
        'volume_24h': '8700.0000',
        'volume_total': '195100.0000',
        'spread_bps': 185,
        'metadata': {'demo': True, 'theme': 'terminal-rate'},
        'snapshots': [
            SnapshotPoint(-30, '0.5600', '126200', '152100', '6100', '60100', '0.0190'),
            SnapshotPoint(-24, '0.5520', '129800', '159000', '6580', '60820', '0.0180'),
            SnapshotPoint(-18, '0.5450', '133500', '166500', '7120', '61540', '0.0170'),
            SnapshotPoint(-12, '0.5370', '137400', '175200', '7630', '62100', '0.0160'),
            SnapshotPoint(-6, '0.5280', '142200', '184900', '8180', '62700', '0.0150'),
            SnapshotPoint(0, '0.5200', '147100', '195100', '8700', '63300', '0.0140'),
        ],
        'rules': [],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'Chip Export Policy 2025 Demo',
        'provider_market_id': 'pm-demo-chip-rules-tighten',
        'ticker': 'DEMO-GEO-EXPORTS',
        'title': 'Will export controls tighten before November 2025?',
        'category': 'geopolitics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.RESOLVED,
        'is_active': False,
        'resolution_source': 'Demo policy bulletin',
        'short_rules': 'Resolved historical market kept for local timeline and status testing.',
        'url': 'https://demo.local/markets/pm-demo-chip-rules-tighten',
        'open_time': timezone.datetime(2025, 7, 1, 12, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2025, 11, 5, 17, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2025, 11, 6, 15, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '1.0000',
        'liquidity': '0.0000',
        'volume_24h': '0.0000',
        'volume_total': '132500.0000',
        'spread_bps': 0,
        'metadata': {'demo': True, 'resolved_outcome': 'yes'},
        'snapshots': [
            SnapshotPoint(-30, '0.4200', '90000', '65000', '5200', '41000', '0.0200'),
            SnapshotPoint(-24, '0.4700', '88000', '76000', '6900', '42000', '0.0190'),
            SnapshotPoint(-18, '0.6100', '86000', '91000', '9800', '43000', '0.0170'),
            SnapshotPoint(-12, '0.7600', '82000', '109000', '12100', '44000', '0.0140'),
            SnapshotPoint(-6, '0.9100', '76000', '125400', '10800', '45200', '0.0100'),
            SnapshotPoint(0, '1.0000', '0', '132500', '0', '0', '0.0000'),
        ],
        'rules': [
            {
                'source_type': RuleSourceType.PROVIDER,
                'rule_text': 'Formal policy publication by the designated authority determines settlement.',
                'resolution_criteria': 'If additional export restrictions are officially announced before the deadline, resolve Yes.',
            },
        ],
    },
    {
        'provider_slug': 'polymarket',
        'event_title': 'Chip Export Policy 2025 Demo',
        'provider_market_id': 'pm-demo-chip-license-window',
        'ticker': 'DEMO-GEO-LICENSE',
        'title': 'Will a temporary export license be extended into Q1 2026?',
        'category': 'geopolitics',
        'market_type': MarketType.BINARY,
        'outcome_type': OutcomeType.YES_NO,
        'status': MarketStatus.CANCELLED,
        'is_active': False,
        'resolution_source': 'Demo policy bulletin',
        'short_rules': 'Cancelled market included so the frontend can render inactive terminal states.',
        'url': 'https://demo.local/markets/pm-demo-chip-license-window',
        'open_time': timezone.datetime(2025, 7, 10, 12, 0, tzinfo=dt_timezone.utc),
        'close_time': timezone.datetime(2025, 10, 15, 17, 0, tzinfo=dt_timezone.utc),
        'resolution_time': timezone.datetime(2025, 10, 16, 15, 0, tzinfo=dt_timezone.utc),
        'current_market_probability': '0.0000',
        'liquidity': '0.0000',
        'volume_24h': '0.0000',
        'volume_total': '48200.0000',
        'spread_bps': 0,
        'metadata': {'demo': True, 'terminal_state': 'cancelled'},
        'snapshots': [
            SnapshotPoint(-30, '0.3300', '52000', '21000', '1800', '14000', '0.0260'),
            SnapshotPoint(-24, '0.3450', '50100', '25500', '2200', '14500', '0.0240'),
            SnapshotPoint(-18, '0.3500', '47000', '30800', '2600', '14900', '0.0230'),
            SnapshotPoint(-12, '0.3420', '41000', '36000', '2800', '15100', '0.0220'),
            SnapshotPoint(-6, '0.3380', '32000', '42800', '3100', '15300', '0.0210'),
            SnapshotPoint(0, '0.0000', '0', '48200', '0', '0', '0.0000'),
        ],
        'rules': [],
    },
]


def quantize_probability(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def derive_price_pair(probability: Decimal) -> tuple[Decimal, Decimal]:
    yes_price = quantize_money(probability * Decimal('100'))
    no_price = quantize_money((Decimal('1') - probability) * Decimal('100'))
    return yes_price, no_price


def derive_order_book(yes_price: Decimal, spread_cents: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    half_spread = quantize_money(spread_cents / Decimal('2'))
    bid = quantize_money(max(Decimal('0'), yes_price - half_spread))
    ask = quantize_money(min(Decimal('100'), yes_price + half_spread))
    spread = quantize_money(ask - bid)
    last_price = quantize_money((bid + ask) / Decimal('2'))
    return bid, ask, spread, last_price


def snapshot_payload(anchor_time, point: SnapshotPoint) -> dict[str, Any]:
    probability = quantize_probability(Decimal(point.probability))
    yes_price, no_price = derive_price_pair(probability)
    bid, ask, spread, last_price = derive_order_book(yes_price, Decimal(point.spread_cents))
    captured_at = anchor_time + timezone.timedelta(hours=point.hours_offset)
    return {
        'captured_at': captured_at,
        'market_probability': probability,
        'yes_price': yes_price,
        'no_price': no_price,
        'last_price': last_price,
        'bid': bid,
        'ask': ask,
        'spread': spread,
        'liquidity': quantize_money(Decimal(point.liquidity)),
        'volume': quantize_money(Decimal(point.volume)),
        'volume_24h': quantize_money(Decimal(point.volume_24h)),
        'open_interest': quantize_money(Decimal(point.open_interest)),
        'metadata': {'demo': True},
    }


@transaction.atomic
def seed_demo_markets(*, stdout=None) -> dict[str, int]:
    providers_by_slug: dict[str, Provider] = {}
    events_by_key: dict[tuple[str, str], Event] = {}
    markets_by_key: dict[tuple[str, str], Market] = {}
    counts = {
        'providers': 0,
        'events': 0,
        'markets': 0,
        'snapshots': 0,
        'rules': 0,
    }

    for provider_data in PROVIDERS:
        provider, _ = Provider.objects.update_or_create(
            slug=provider_data['slug'],
            defaults=provider_data,
        )
        providers_by_slug[provider.slug] = provider
        counts['providers'] += 1

    for event_data in EVENTS:
        provider = providers_by_slug[event_data['provider_slug']]
        defaults = {key: value for key, value in event_data.items() if key != 'provider_slug'}
        event, _ = Event.objects.update_or_create(
            provider=provider,
            slug=slugify(defaults['title']),
            defaults=defaults,
        )
        if event.provider_event_id != defaults['provider_event_id']:
            event.provider_event_id = defaults['provider_event_id']
            event.save(update_fields=['provider_event_id', 'updated_at'])
        events_by_key[(provider.slug, event.title)] = event
        counts['events'] += 1

    for market_data in MARKETS:
        provider = providers_by_slug[market_data['provider_slug']]
        event = events_by_key[(provider.slug, market_data['event_title'])]
        defaults = {
            key: value
            for key, value in market_data.items()
            if key not in {'provider_slug', 'event_title', 'snapshots', 'rules'}
        }
        defaults['provider'] = provider
        defaults['event'] = event
        current_probability = quantize_probability(Decimal(str(defaults['current_market_probability'])))
        current_yes_price, current_no_price = derive_price_pair(current_probability)
        defaults['current_market_probability'] = current_probability
        defaults['current_yes_price'] = current_yes_price
        defaults['current_no_price'] = current_no_price
        defaults['liquidity'] = quantize_money(Decimal(str(defaults['liquidity'])))
        defaults['volume_24h'] = quantize_money(Decimal(str(defaults['volume_24h'])))
        defaults['volume_total'] = quantize_money(Decimal(str(defaults['volume_total'])))

        market, _ = Market.objects.update_or_create(
            provider=provider,
            slug=slugify(defaults['title']),
            defaults=defaults,
        )
        if market.provider_market_id != defaults['provider_market_id']:
            market.provider_market_id = defaults['provider_market_id']
            market.save(update_fields=['provider_market_id', 'updated_at'])
        markets_by_key[(provider.slug, market.title)] = market
        counts['markets'] += 1

        snapshot_anchor = max(
            [value for value in [market.open_time, market.close_time, market.resolution_time, SEED_GENERATED_AT] if value],
            key=lambda value: value,
        )
        if market.status in {MarketStatus.OPEN, MarketStatus.PAUSED}:
            snapshot_anchor = min(snapshot_anchor, SEED_GENERATED_AT)

        for point in market_data['snapshots']:
            payload = snapshot_payload(snapshot_anchor, point)
            MarketSnapshot.objects.update_or_create(
                market=market,
                captured_at=payload['captured_at'],
                defaults=payload,
            )
            counts['snapshots'] += 1

        for rule in market_data['rules']:
            MarketRule.objects.update_or_create(
                market=market,
                source_type=rule['source_type'],
                rule_text=rule['rule_text'],
                defaults={'resolution_criteria': rule.get('resolution_criteria', '')},
            )
            counts['rules'] += 1

    if stdout is not None:
        stdout.write(
            f"Seeded demo data at {timezone.localtime(SEED_GENERATED_AT).isoformat()} "
            f"with {counts['providers']} providers, {counts['events']} events, "
            f"{counts['markets']} markets, {counts['snapshots']} snapshots, and {counts['rules']} rules."
        )

    return counts
