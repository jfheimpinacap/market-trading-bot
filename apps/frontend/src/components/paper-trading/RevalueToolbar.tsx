import { StatusBadge } from '../dashboard/StatusBadge';

type RevalueToolbarProps = {
  onRevalue: () => void;
  isRefreshing: boolean;
  statusMessage: string | null;
  errorMessage: string | null;
  lastUpdatedLabel: string;
};

export function RevalueToolbar({
  onRevalue,
  isRefreshing,
  statusMessage,
  errorMessage,
  lastUpdatedLabel,
}: RevalueToolbarProps) {
  return (
    <div className="paper-toolbar">
      <div className="paper-toolbar__meta">
        <StatusBadge tone={errorMessage ? 'offline' : isRefreshing ? 'loading' : 'ready'}>
          {errorMessage ? 'Revalue failed' : isRefreshing ? 'Revaluing portfolio' : 'Paper trading demo'}
        </StatusBadge>
        <span className="muted-text">{errorMessage ?? statusMessage ?? lastUpdatedLabel}</span>
      </div>
      <button className="secondary-button" type="button" onClick={onRevalue} disabled={isRefreshing}>
        {isRefreshing ? 'Revaluing…' : 'Revalue portfolio'}
      </button>
    </div>
  );
}
