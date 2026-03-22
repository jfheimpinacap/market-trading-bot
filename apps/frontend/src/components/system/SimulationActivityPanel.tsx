import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import { SectionCard } from '../SectionCard';
import { DataStateWrapper } from '../markets/DataStateWrapper';
import { StatusBadge } from '../dashboard/StatusBadge';
import type { SimulationActivityItem, SimulationObservation } from '../../types/system';

function formatTimestamp(value: string | null) {
  if (!value) {
    return 'Not available';
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

function formatCompactNumber(value: string | number | null) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(numericValue);
}

function formatProbability(value: string | null) {
  if (!value) {
    return '—';
  }

  const numericValue = Number(value);
  if (Number.isNaN(numericValue)) {
    return value;
  }

  return `${Math.round(numericValue * 100)}%`;
}

function getActivityTimestamp(item: SimulationActivityItem) {
  return item.latestSnapshotAt ?? item.updatedAt;
}

export function SimulationActivityPanel({
  items,
  observations,
  isLoading,
  errorMessage,
}: {
  items: SimulationActivityItem[];
  observations: SimulationObservation[];
  isLoading: boolean;
  errorMessage?: string | null;
}) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <SectionCard
      eyebrow="Observed activity"
      title="Simulation activity view"
      description="This section uses only existing read-only endpoints. Activity signals are inferred from snapshot timestamps, snapshot totals, and market field changes across refreshes."
      aside={<StatusBadge tone="neutral">Inference from current data</StatusBadge>}
    >
      <DataStateWrapper
        isLoading={isLoading}
        isError={Boolean(errorMessage)}
        errorMessage={errorMessage ?? undefined}
        isEmpty={!isLoading && !errorMessage && items.length === 0}
        loadingTitle="Loading observable activity"
        loadingDescription="Requesting the market list so the page can infer recent simulation movement."
        errorTitle="Could not load observable activity"
        emptyTitle="No seeded markets available yet"
        emptyDescription="Run `python manage.py seed_markets_demo` and refresh this page to inspect local market activity."
      >
        <div className="system-observation-grid">
          {observations.map((observation) => (
            <article key={observation.label} className="system-observation-card">
              <div className="system-observation-card__header">
                <span>{observation.label}</span>
                <StatusBadge tone={observation.tone}>{observation.badge}</StatusBadge>
              </div>
              <strong>{observation.value}</strong>
              <p>{observation.helperText}</p>
            </article>
          ))}
        </div>

        <div className="dashboard-recent-list">
          {items.map((item) => (
            <a
              key={item.id}
              className="dashboard-recent-list__item system-activity-item"
              href={`/markets/${item.id}`}
              onClick={(event) => handleClick(event, `/markets/${item.id}`)}
            >
              <div className="dashboard-recent-list__header">
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.eventTitle ?? item.providerName}</p>
                </div>
                <div className="system-activity-item__badges">
                  <StatusBadge tone="neutral">{item.status}</StatusBadge>
                  <StatusBadge tone={item.activitySource === 'latest_snapshot_at' ? 'ready' : 'loading'}>
                    {item.activitySource === 'latest_snapshot_at' ? 'Snapshot-driven' : 'Updated fallback'}
                  </StatusBadge>
                </div>
              </div>

              <dl className="system-activity-item__meta">
                <div>
                  <dt>Provider</dt>
                  <dd>{item.providerName}</dd>
                </div>
                <div>
                  <dt>Observed at</dt>
                  <dd>{formatTimestamp(getActivityTimestamp(item))}</dd>
                </div>
                <div>
                  <dt>Snapshots</dt>
                  <dd>{formatCompactNumber(item.snapshotCount)}</dd>
                </div>
                <div>
                  <dt>Probability</dt>
                  <dd>{formatProbability(item.probability)}</dd>
                </div>
                <div>
                  <dt>Liquidity</dt>
                  <dd>{formatCompactNumber(item.liquidity)}</dd>
                </div>
                <div>
                  <dt>Volume 24h</dt>
                  <dd>{formatCompactNumber(item.volume24h)}</dd>
                </div>
              </dl>
            </a>
          ))}
        </div>
      </DataStateWrapper>
    </SectionCard>
  );
}
