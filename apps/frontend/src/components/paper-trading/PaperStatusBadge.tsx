import { titleize } from '../markets/utils';

type PaperStatusBadgeProps = {
  value: string;
};

export function PaperStatusBadge({ value }: PaperStatusBadgeProps) {
  const normalized = value.toLowerCase();
  return <span className={`paper-badge paper-badge--status paper-badge--${normalized}`}>{titleize(value)}</span>;
}
