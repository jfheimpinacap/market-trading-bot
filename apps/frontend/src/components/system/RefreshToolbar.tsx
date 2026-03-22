import { StatusBadge } from '../dashboard/StatusBadge';

type RefreshToolbarProps = {
  lastRefreshedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
};

function formatTimestamp(value: string | null) {
  if (!value) {
    return 'Pending first refresh';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function RefreshToolbar({ lastRefreshedAt, isRefreshing, onRefresh }: RefreshToolbarProps) {
  return (
    <div className="system-toolbar">
      <StatusBadge tone="ready">Local demo</StatusBadge>
      <div className="system-toolbar__meta">
        <span className="muted-text">Last refreshed: {formatTimestamp(lastRefreshedAt)}</span>
        <button className="secondary-button" type="button" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? 'Refreshing…' : 'Refresh system data'}
        </button>
      </div>
    </div>
  );
}
