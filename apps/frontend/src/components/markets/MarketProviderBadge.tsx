type MarketProviderBadgeProps = {
  providerName: string;
};

function getProviderTone(providerName: string) {
  const normalized = providerName.trim().toLowerCase();

  if (normalized.includes('kalshi')) {
    return 'market-badge--provider-kalshi';
  }

  if (normalized.includes('polymarket')) {
    return 'market-badge--provider-polymarket';
  }

  return 'market-badge--status';
}

export function MarketProviderBadge({ providerName }: MarketProviderBadgeProps) {
  return <span className={`market-badge ${getProviderTone(providerName)}`}>{providerName}</span>;
}
