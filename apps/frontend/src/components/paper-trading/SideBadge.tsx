import { formatSideLabel } from './utils';

type SideBadgeProps = {
  side: string;
};

export function SideBadge({ side }: SideBadgeProps) {
  const normalized = side.toLowerCase();
  return <span className={`paper-badge paper-badge--side paper-badge--${normalized}`}>{formatSideLabel(side)}</span>;
}
