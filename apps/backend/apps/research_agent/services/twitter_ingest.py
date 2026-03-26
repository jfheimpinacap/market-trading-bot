from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
import json
from urllib import parse, request

from apps.research_agent.models import NarrativeItem, NarrativeSource, NarrativeSourceType
from apps.research_agent.services.ingest import IngestResult, build_dedupe_hash

DEFAULT_LIMIT = 20


@dataclass
class TwitterSourceAdapter:
    source: NarrativeSource

    def fetch(self) -> list[dict]:
        metadata = self.source.metadata or {}
        manual_items = metadata.get('manual_items')
        if isinstance(manual_items, list):
            return manual_items

        endpoint_url = str(metadata.get('endpoint_url') or '').strip()
        if not endpoint_url:
            raise ValueError('twitter source requires metadata.manual_items or metadata.endpoint_url')

        fetch_limit = int(metadata.get('fetch_limit') or DEFAULT_LIMIT)
        query = str(metadata.get('query') or metadata.get('hashtag') or '').strip()
        account = str(metadata.get('account') or '').strip().lstrip('@')

        query_params = {'limit': max(1, min(fetch_limit, 100))}
        if query:
            query_params['query'] = query
        if account:
            query_params['account'] = account
        delimiter = '&' if '?' in endpoint_url else '?'
        url = f"{endpoint_url}{delimiter}{parse.urlencode(query_params)}"

        headers = {'User-Agent': 'market-trading-bot/1.0 (research scan twitter adapter)'}
        bearer = str(metadata.get('bearer_token') or '').strip()
        if bearer:
            headers['Authorization'] = f'Bearer {bearer}'

        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode('utf-8'))

        items = payload.get('items') if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ValueError('twitter adapter expected JSON object with items list')
        return items


def _normalize_url(value: str) -> str:
    url = (value or '').strip()
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return f'https://x.com{url}'
    return f'https://x.com/{url.lstrip("/")}'


def _safe_created_at(value: str | int | float | None):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=dt_timezone.utc)
        except (TypeError, ValueError):
            return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.endswith('Z'):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_timezone.utc)


def _extract_post_text(post: dict) -> str:
    return str(post.get('text') or post.get('full_text') or post.get('content') or '').strip()


def run_twitter_ingest(*, source_ids: list[int] | None = None) -> IngestResult:
    sources = NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.TWITTER)
    if source_ids:
        sources = sources.filter(id__in=source_ids)

    result = IngestResult(sources_scanned=sources.count())

    for source in sources:
        adapter = TwitterSourceAdapter(source=source)
        try:
            posts = adapter.fetch()
        except Exception as exc:
            result.add_error(source.slug, str(exc))
            continue

        for post in posts:
            if not isinstance(post, dict):
                continue
            text = _extract_post_text(post)
            if not text:
                continue

            external_id = str(post.get('id') or post.get('tweet_id') or post.get('external_id') or '').strip() or None
            author = str(post.get('author') or post.get('handle') or post.get('username') or '').strip().lstrip('@')
            created_at = _safe_created_at(post.get('created_at') or post.get('timestamp'))
            permalink = _normalize_url(str(post.get('url') or post.get('permalink') or ''))
            if not permalink and external_id and author:
                permalink = f'https://x.com/{author}/status/{external_id}'
            if not permalink:
                permalink = 'https://x.com'

            dedupe_hash = build_dedupe_hash(
                source_slug=source.slug,
                title=text[:160],
                url=permalink,
                external_id=external_id,
                published=created_at.isoformat() if created_at else None,
            )
            if NarrativeItem.objects.filter(dedupe_hash=dedupe_hash).exists():
                result.items_deduplicated += 1
                continue

            engagement = {
                'likes': int(post.get('like_count') or post.get('likes') or 0),
                'retweets': int(post.get('retweet_count') or post.get('retweets') or 0),
                'replies': int(post.get('reply_count') or post.get('replies') or 0),
                'quotes': int(post.get('quote_count') or post.get('quotes') or 0),
            }
            title = text[:220]
            NarrativeItem.objects.create(
                source=source,
                external_id=external_id,
                title=title[:512],
                url=permalink,
                published_at=created_at,
                raw_text=text[:8000],
                snippet=text[:1000],
                author=author[:255],
                source_name=(f'@{author}' if author else source.name)[:255],
                dedupe_hash=dedupe_hash,
                metadata={
                    'twitter': {
                        'author': author,
                        'query': source.metadata.get('query') if isinstance(source.metadata, dict) else None,
                        'engagement': engagement,
                    },
                    'narrative_source_type': 'social_twitter',
                },
            )
            result.items_created += 1
            result.twitter_items_created += 1
            result.social_items_total += 1

    return result
