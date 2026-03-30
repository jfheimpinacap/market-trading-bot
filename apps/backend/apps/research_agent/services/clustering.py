from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from apps.research_agent.services.source_fetch import ScanRawItem


@dataclass
class ClusterBundle:
    key: str
    topic: str
    representative_headline: str
    items: list[ScanRawItem]


STOP_WORDS = {'the', 'and', 'for', 'will', 'with', 'this', 'that', 'from', 'into', 'about', 'market'}


def _topic_from_item(item: ScanRawItem) -> str:
    tokens = re.findall(r'[a-z0-9]+', item.title.lower())
    meaningful = [token for token in tokens if token not in STOP_WORDS and len(token) > 2]
    if not meaningful:
        return item.title[:80].lower() or 'uncategorized'
    return ' '.join(meaningful[:4])


def cluster_narratives(items: list[ScanRawItem]) -> list[ClusterBundle]:
    grouped: dict[str, list[ScanRawItem]] = defaultdict(list)
    for item in items:
        key = _topic_from_item(item)
        grouped[key].append(item)

    bundles: list[ClusterBundle] = []
    for key, grouped_items in grouped.items():
        bundles.append(
            ClusterBundle(
                key=key,
                topic=key,
                representative_headline=grouped_items[0].title,
                items=grouped_items,
            )
        )
    return sorted(bundles, key=lambda cluster: len(cluster.items), reverse=True)
