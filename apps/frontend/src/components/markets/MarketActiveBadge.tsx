
type MarketActiveBadgeProps = {
  isActive: boolean;
};

export function MarketActiveBadge({ isActive }: MarketActiveBadgeProps) {
  return (
    <span className={`market-badge market-badge--active ${isActive ? 'market-badge--online' : 'market-badge--offline'}`}>
      {isActive ? 'Active' : 'Inactive'}
    </span>
  );
}
