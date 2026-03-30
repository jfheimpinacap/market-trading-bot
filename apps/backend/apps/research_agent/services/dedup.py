from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from apps.research_agent.services.source_fetch import ScanRawItem


@dataclass
class DedupResult:
    deduped_items: list[ScanRawItem]
    ignored_items: list[ScanRawItem]


def _norm_text(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').lower()).strip()


def _item_fingerprint(item: ScanRawItem) -> str:
    normalized = '|'.join([_norm_text(item.title), _norm_text(item.url), _norm_text(item.raw_text[:240])])
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def deduplicate_narratives(items: list[ScanRawItem]) -> DedupResult:
    seen: set[str] = set()
    deduped: list[ScanRawItem] = []
    ignored: list[ScanRawItem] = []
    for item in items:
        fp = _item_fingerprint(item)
        if fp in seen:
            ignored.append(item)
            continue
        seen.add(fp)
        deduped.append(item)
    return DedupResult(deduped_items=deduped, ignored_items=ignored)
