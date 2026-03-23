import { getPnlTone } from './utils';

type PnlBadgeProps = {
  value: number | string | null | undefined;
  children: string;
};

export function PnlBadge({ value, children }: PnlBadgeProps) {
  const tone = getPnlTone(value);

  return <span className={`paper-badge paper-badge--pnl paper-badge--${tone}`}>{children}</span>;
}
