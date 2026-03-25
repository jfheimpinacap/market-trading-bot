from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from urllib import request
from xml.etree import ElementTree

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.research_agent.models import NarrativeItem, NarrativeSource, NarrativeSourceType


@dataclass
class IngestResult:
    sources_scanned: int = 0
    items_created: int = 0
    items_deduplicated: int = 0
    errors: list[str] | None = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _safe_datetime(value: str | None):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed
    for fmt in ('%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _text(element, tag: str) -> str:
    found = element.find(tag)
    return (found.text or '').strip() if found is not None and found.text else ''


def parse_rss(xml_text: str) -> dict:
    root = ElementTree.fromstring(xml_text)
    channel = root.find('channel')
    feed_title = _text(channel, 'title') if channel is not None else ''
    entries = []
    for item in root.findall('./channel/item'):
        entries.append(
            {
                'title': _text(item, 'title'),
                'link': _text(item, 'link'),
                'id': _text(item, 'guid') or _text(item, 'link'),
                'published': _text(item, 'pubDate'),
                'author': _text(item, 'author'),
                'summary': _text(item, 'description'),
                'content': _text(item, 'content'),
            }
        )
    return {'feed': {'title': feed_title}, 'entries': entries}


def fetch_rss(source: NarrativeSource) -> dict:
    with request.urlopen(source.feed_url, timeout=20) as response:
        body = response.read().decode('utf-8', errors='ignore')
    return parse_rss(body)


def build_dedupe_hash(*, source_slug: str, title: str, url: str, external_id: str | None, published: str | None) -> str:
    normalized = '|'.join(
        [
            source_slug.strip().lower(),
            (title or '').strip().lower(),
            (url or '').strip().lower(),
            (external_id or '').strip().lower(),
            (published or '').strip().lower(),
        ]
    )
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _extract_text(entry: dict) -> tuple[str, str]:
    snippet = str(entry.get('summary') or '').strip()
    raw = str(entry.get('content') or '').strip() or snippet
    return raw[:8000], snippet[:1000]


def run_rss_ingest(*, source_ids: list[int] | None = None) -> IngestResult:
    sources = NarrativeSource.objects.filter(is_enabled=True, source_type=NarrativeSourceType.RSS)
    if source_ids:
        sources = sources.filter(id__in=source_ids)

    result = IngestResult(sources_scanned=sources.count())

    for source in sources:
        try:
            parsed = fetch_rss(source)
        except Exception as exc:
            result.errors.append(f'Source {source.slug}: {exc}')
            continue

        for entry in parsed.get('entries', []):
            title = str(entry.get('title') or '').strip()
            url = str(entry.get('link') or '').strip()
            if not title or not url:
                continue

            external_id = str(entry.get('id') or '').strip() or None
            published_raw = str(entry.get('published') or '').strip() or None
            dedupe_hash = build_dedupe_hash(
                source_slug=source.slug,
                title=title,
                url=url,
                external_id=external_id,
                published=published_raw,
            )
            if NarrativeItem.objects.filter(dedupe_hash=dedupe_hash).exists():
                result.items_deduplicated += 1
                continue

            raw_text, snippet = _extract_text(entry)
            published_at = _safe_datetime(published_raw)
            NarrativeItem.objects.create(
                source=source,
                external_id=external_id,
                title=title[:512],
                url=url,
                published_at=published_at,
                raw_text=raw_text or title,
                snippet=snippet,
                author=str(entry.get('author') or '').strip()[:255],
                source_name=str((parsed.get('feed') or {}).get('title') or source.name).strip()[:255],
                dedupe_hash=dedupe_hash,
                ingested_at=timezone.now(),
                metadata={'rss_source_type': 'rss'},
            )
            result.items_created += 1

    return result
