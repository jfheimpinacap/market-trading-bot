import type { MarketListItem } from '../../types/markets';

type MarketSourceBadgeProps = {
  sourceType: MarketListItem['source_type'];
};

function getTone(sourceType: MarketListItem['source_type']) {
  if (sourceType === 'real_read_only') {
    return 'market-badge--real';
  }

  if (sourceType === 'demo') {
    return 'market-badge--demo';
  }

  return 'market-badge--status';
}

function getLabel(sourceType: MarketListItem['source_type']) {
  if (sourceType === 'real_read_only') {
    return 'REAL · READ-ONLY';
  }

  if (sourceType === 'demo') {
    return 'DEMO';
  }

  return sourceType || 'Unknown source';
}

export function MarketSourceBadge({ sourceType }: MarketSourceBadgeProps) {
  return <span className={`market-badge ${getTone(sourceType)}`}>{getLabel(sourceType)}</span>;
}
