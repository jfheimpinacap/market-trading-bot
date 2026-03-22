import type { ReactNode } from 'react';

type StatusBadgeTone = 'online' | 'offline' | 'loading' | 'ready' | 'pending' | 'neutral';

type StatusBadgeProps = {
  tone: StatusBadgeTone;
  children: ReactNode;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`dashboard-badge dashboard-badge--${tone}`}>{children}</span>;
}
