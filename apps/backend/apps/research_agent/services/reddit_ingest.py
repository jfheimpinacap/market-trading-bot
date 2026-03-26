from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
import json
from urllib import parse, request

from apps.research_agent.models import NarrativeItem, NarrativeSource, NarrativeSourceType
from apps.research_agent.services.ingest import IngestResult, build_dedupe_hash

DEFAULT_LIMIT = 20


def _normalize_reddit_url(raw_url: str) -> str:
    value = (raw_url or '').strip()
    if not value:
        return ''
    if value.startswith('http://') or value.startswith('https://'):
        return value
    if value.startswith('/'):
        return f'https://www.reddit.com{value}'
    return f'https://{value}'


def _fetch_reddit_listing(*, subreddit: str, listing: str, fetch_limit: int) -> dict:
    query = parse.urlencode({'limit': max(1, min(fetch_limit, 100)), 'raw_json': 1})
    url = f'https://www.reddit.com/r/{subreddit}/{listing}.json?{query}'
    req = request.Request(url, headers={'User-Agent': 'market-trading-bot/1.0 (research scan)'})
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def run_reddit_ingest(*, source_ids: list[int] | None = None) -> IngestResult:
    sources = NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.REDDIT)
    if source_ids:
        sources = sources.filter(id__in=source_ids)

    result = IngestResult(sources_scanned=sources.count())

    for source in sources:
        subreddit = str(source.metadata.get('subreddit') or source.category or source.slug).replace('r/', '').strip('/')
        listing = str(source.metadata.get('listing') or 'hot').lower()
        if listing not in {'hot', 'new', 'top'}:
            listing = 'hot'
        fetch_limit = int(source.metadata.get('fetch_limit') or DEFAULT_LIMIT)

        if not subreddit:
            result.add_error(source.slug, 'reddit source missing subreddit in metadata.subreddit/category/slug')
            continue

        try:
            payload = _fetch_reddit_listing(subreddit=subreddit, listing=listing, fetch_limit=fetch_limit)
        except Exception as exc:
            result.add_error(source.slug, str(exc))
            continue

        children = ((payload.get('data') or {}).get('children') or [])
        for child in children:
            data = child.get('data') or {}
            title = str(data.get('title') or '').strip()
            permalink = _normalize_reddit_url(str(data.get('permalink') or ''))
            canonical_url = _normalize_reddit_url(str(data.get('url_overridden_by_dest') or data.get('url') or permalink))
            if not title or not canonical_url:
                continue

            external_id = str(data.get('id') or '').strip() or None
            created_utc = data.get('created_utc')
            published_at = None
            if created_utc is not None:
                try:
                    published_at = datetime.fromtimestamp(float(created_utc), tz=dt_timezone.utc)
                except (TypeError, ValueError):
                    published_at = None

            dedupe_hash = build_dedupe_hash(
                source_slug=source.slug,
                title=title,
                url=canonical_url,
                external_id=external_id,
                published=published_at.isoformat() if published_at else None,
            )
            if NarrativeItem.objects.filter(dedupe_hash=dedupe_hash).exists():
                result.items_deduplicated += 1
                continue

            selftext = str(data.get('selftext') or '').strip()
            snippet = selftext[:1000]
            raw_text = f"{title}\n\n{selftext}".strip()[:8000]
            NarrativeItem.objects.create(
                source=source,
                external_id=external_id,
                title=title[:512],
                url=canonical_url,
                published_at=published_at,
                raw_text=raw_text or title,
                snippet=snippet,
                author=str(data.get('author') or '').strip()[:255],
                source_name=f'r/{subreddit}'[:255],
                dedupe_hash=dedupe_hash,
                metadata={
                    'reddit': {
                        'subreddit': subreddit,
                        'listing': listing,
                        'score': int(data.get('score') or 0),
                        'permalink': permalink,
                        'num_comments': int(data.get('num_comments') or 0),
                    },
                    'narrative_source_type': 'social_reddit',
                },
            )
            result.items_created += 1
            result.reddit_items_created += 1

    return result
