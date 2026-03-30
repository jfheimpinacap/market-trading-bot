from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from apps.research_agent.models import NarrativeSource, NarrativeSourceType
from apps.research_agent.services.ingest import fetch_rss
from apps.research_agent.services.reddit_ingest import _fetch_reddit_listing
from apps.research_agent.services.twitter_ingest import TwitterSourceAdapter


@dataclass
class ScanRawItem:
    source_type: str
    source_slug: str
    source_name: str
    title: str
    url: str
    raw_text: str
    snippet: str
    author: str
    published_at: datetime | None
    metadata: dict


def _safe_url(value: str) -> str:
    url = (value or '').strip()
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return f'https://www.reddit.com{url}'
    return f'https://{url}'


def fetch_parallel_source_items(*, source_ids: list[int] | None = None) -> tuple[list[ScanRawItem], dict[str, int], list[str]]:
    queryset = NarrativeSource.objects.filter(is_enabled=True)
    if source_ids:
        queryset = queryset.filter(id__in=source_ids)

    items: list[ScanRawItem] = []
    errors: list[str] = []
    source_counts = {'rss_count': 0, 'reddit_count': 0, 'x_count': 0}

    for source in queryset:
        if source.source_type == NarrativeSourceType.RSS:
            try:
                payload = fetch_rss(source)
            except Exception as exc:  # pragma: no cover - network path
                errors.append(f'{source.slug}: {exc}')
                continue
            for entry in payload.get('entries', []):
                title = str(entry.get('title') or '').strip()
                url = str(entry.get('link') or '').strip()
                if not title or not url:
                    continue
                source_counts['rss_count'] += 1
                snippet = str(entry.get('summary') or '')[:1000]
                raw_text = str(entry.get('content') or snippet or title)[:8000]
                items.append(
                    ScanRawItem(
                        source_type='rss',
                        source_slug=source.slug,
                        source_name=source.name,
                        title=title[:512],
                        url=url,
                        raw_text=raw_text,
                        snippet=snippet,
                        author=str(entry.get('author') or '')[:255],
                        published_at=timezone.now(),
                        metadata={'external_id': entry.get('id')},
                    )
                )
        elif source.source_type == NarrativeSourceType.REDDIT:
            subreddit = str(source.metadata.get('subreddit') or source.category or source.slug).replace('r/', '').strip('/')
            listing = str(source.metadata.get('listing') or 'hot').lower()
            fetch_limit = int(source.metadata.get('fetch_limit') or 20)
            try:
                payload = _fetch_reddit_listing(subreddit=subreddit, listing=listing, fetch_limit=fetch_limit)
            except Exception as exc:  # pragma: no cover - network path
                errors.append(f'{source.slug}: {exc}')
                continue
            for child in ((payload.get('data') or {}).get('children') or []):
                data = child.get('data') or {}
                title = str(data.get('title') or '').strip()
                url = _safe_url(str(data.get('url_overridden_by_dest') or data.get('url') or data.get('permalink') or ''))
                if not title or not url:
                    continue
                source_counts['reddit_count'] += 1
                selftext = str(data.get('selftext') or '')
                items.append(
                    ScanRawItem(
                        source_type='reddit',
                        source_slug=source.slug,
                        source_name=f'r/{subreddit}',
                        title=title[:512],
                        url=url,
                        raw_text=f'{title}\n\n{selftext}'.strip()[:8000],
                        snippet=selftext[:1000],
                        author=str(data.get('author') or '')[:255],
                        published_at=timezone.now(),
                        metadata={'score': int(data.get('score') or 0), 'comments': int(data.get('num_comments') or 0), 'external_id': data.get('id')},
                    )
                )
        elif source.source_type == NarrativeSourceType.TWITTER:
            try:
                posts = TwitterSourceAdapter(source=source).fetch()
            except Exception as exc:  # pragma: no cover - network path
                errors.append(f'{source.slug}: {exc}')
                continue
            for post in posts:
                if not isinstance(post, dict):
                    continue
                text = str(post.get('text') or post.get('full_text') or post.get('content') or '').strip()
                if not text:
                    continue
                source_counts['x_count'] += 1
                items.append(
                    ScanRawItem(
                        source_type='x',
                        source_slug=source.slug,
                        source_name=source.name,
                        title=text[:220],
                        url=str(post.get('url') or post.get('permalink') or 'https://x.com'),
                        raw_text=text[:8000],
                        snippet=text[:1000],
                        author=str(post.get('author') or post.get('username') or '')[:255],
                        published_at=timezone.now(),
                        metadata={
                            'likes': int(post.get('like_count') or 0),
                            'retweets': int(post.get('retweet_count') or 0),
                            'replies': int(post.get('reply_count') or 0),
                            'external_id': post.get('id'),
                        },
                    )
                )

    return items, source_counts, errors
