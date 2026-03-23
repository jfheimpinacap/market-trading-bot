import { titleize } from '../markets/utils';

type BadgeProps = {
  value: string;
  kind: 'direction' | 'status' | 'actionable';
};

function getClassName(kind: BadgeProps['kind'], value: string) {
  const normalized = value.toLowerCase();

  if (kind === 'direction') {
    if (normalized === 'bullish') {
      return 'signal-badge signal-badge--bullish';
    }
    if (normalized === 'bearish') {
      return 'signal-badge signal-badge--bearish';
    }
    return 'signal-badge signal-badge--neutral';
  }

  if (kind === 'actionable') {
    return normalized === 'actionable' ? 'signal-badge signal-badge--actionable' : 'signal-badge signal-badge--muted';
  }

  if (normalized === 'active') {
    return 'signal-badge signal-badge--actionable';
  }
  if (normalized === 'monitor') {
    return 'signal-badge signal-badge--monitor';
  }
  if (normalized === 'expired' || normalized === 'superseded') {
    return 'signal-badge signal-badge--muted';
  }
  return 'signal-badge signal-badge--neutral';
}

export function SignalBadge({ value, kind }: BadgeProps) {
  const label = kind === 'actionable' ? value : titleize(value);
  return <span className={getClassName(kind, value)}>{label}</span>;
}
