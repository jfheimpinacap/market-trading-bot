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

function getLabel(kind: BadgeProps['kind'], value: string) {
  if (kind === 'actionable') {
    return value;
  }

  return titleize(value);
}

export function SignalBadge({ value, kind }: BadgeProps) {
  return <span className={getClassName(kind, value)}>{getLabel(kind, value)}</span>;
}
