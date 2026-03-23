import { useMemo, useState } from 'react';
import { SectionCard } from '../SectionCard';
import { formatDateTime, formatPercent, formatNumber } from './utils';
import { hasHistorySeries, mapSnapshotsToMarketHistoryPoints } from './marketHistory';
import type { MarketSnapshot } from '../../types/markets';

type MarketHistoryChartProps = {
  snapshots: MarketSnapshot[];
  isLoading?: boolean;
  error?: string | null;
};

type HistorySeriesKey = 'marketProbability' | 'yesPrice' | 'noPrice';

type SeriesConfig = {
  key: HistorySeriesKey;
  label: string;
  color: string;
  strokeWidth: number;
};

const CHART_WIDTH = 760;
const CHART_HEIGHT = 320;
const PADDING = { top: 20, right: 20, bottom: 48, left: 52 };
const SERIES: SeriesConfig[] = [
  { key: 'marketProbability', label: 'Market probability', color: '#4cc9f0', strokeWidth: 3 },
  { key: 'yesPrice', label: 'Yes price', color: '#52b788', strokeWidth: 2 },
  { key: 'noPrice', label: 'No price', color: '#c77dff', strokeWidth: 2 },
];
const Y_AXIS_TICKS = [0, 0.25, 0.5, 0.75, 1];

function clampUnitInterval(value: number | null) {
  if (value === null) {
    return null;
  }

  return Math.min(1, Math.max(0, value));
}

function buildLinePath(points: Array<{ x: number; y: number | null }>) {
  const commands: string[] = [];
  let previousY: number | null = null;

  points.forEach((point) => {
    if (point.y === null) {
      previousY = null;
      return;
    }

    const prefix = previousY === null ? 'M' : 'L';
    commands.push(`${prefix} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`);
    previousY = point.y;
  });

  return commands.join(' ');
}

export function MarketHistoryChart({ snapshots, isLoading = false, error = null }: MarketHistoryChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const historyPoints = useMemo(() => mapSnapshotsToMarketHistoryPoints(snapshots), [snapshots]);

  const series = useMemo(
    () => SERIES.filter((entry) => entry.key === 'marketProbability' || hasHistorySeries(historyPoints, entry.key)),
    [historyPoints],
  );

  const domain = {
    minX: PADDING.left,
    maxX: CHART_WIDTH - PADDING.right,
    minY: PADDING.top,
    maxY: CHART_HEIGHT - PADDING.bottom,
  };

  const chartPoints = historyPoints.map((point, index) => {
    const denominator = Math.max(historyPoints.length - 1, 1);
    const x = domain.minX + ((domain.maxX - domain.minX) * index) / denominator;

    const projectY = (value: number | null) => {
      const clamped = clampUnitInterval(value);
      if (clamped === null) {
        return null;
      }

      return domain.maxY - clamped * (domain.maxY - domain.minY);
    };

    return {
      ...point,
      x,
      yValues: {
        marketProbability: projectY(point.marketProbability),
        yesPrice: projectY(point.yesPrice),
        noPrice: projectY(point.noPrice),
      },
    };
  });

  const latestPoint = historyPoints.length > 0 ? historyPoints[historyPoints.length - 1] : null;
  const firstPoint = historyPoints[0] ?? null;
  const activeTooltipPoint = hoveredIndex === null
    ? chartPoints.length > 0
      ? chartPoints[chartPoints.length - 1]
      : null
    : chartPoints[hoveredIndex] ?? null;
  const xAxisLabels = [
    chartPoints[0],
    chartPoints[Math.floor((chartPoints.length - 1) / 2)],
    chartPoints.length > 0 ? chartPoints[chartPoints.length - 1] : undefined,
  ].filter((value, index, values): value is (typeof chartPoints)[number] => Boolean(value) && values.indexOf(value) === index);

  const notEnoughPoints = historyPoints.length < 2;

  return (
    <SectionCard
      eyebrow="History"
      title="Market history"
      description="Simple snapshot-based view of how this market has moved over time. The chart updates naturally when new backend snapshots are created."
      aside={
        <div className="market-history-summary">
          <div>
            <span>Latest probability</span>
            <strong>{formatPercent(latestPoint?.marketProbability ?? null)}</strong>
          </div>
          <div>
            <span>Snapshots</span>
            <strong>{formatNumber(historyPoints.length)}</strong>
          </div>
          <div>
            <span>History window</span>
            <strong>{firstPoint && latestPoint ? `${formatDateTime(firstPoint.capturedAt)} → ${formatDateTime(latestPoint.capturedAt)}` : '—'}</strong>
          </div>
        </div>
      }
    >
      {isLoading ? <p className="muted-text">Loading market history from recent snapshots…</p> : null}
      {!isLoading && error ? <p className="market-history-state market-history-state--error">Could not load market history. {error}</p> : null}
      {!isLoading && !error && historyPoints.length === 0 ? (
        <p className="market-history-state">No snapshots yet for this market. Run the simulator once to capture the first historical point.</p>
      ) : null}
      {!isLoading && !error && historyPoints.length > 0 ? (
        <div className="market-history-chart">
          <div className="market-history-chart__legend">
            {series.map((entry) => (
              <span key={entry.key} className="market-history-chart__legend-item">
                <i style={{ backgroundColor: entry.color }} aria-hidden="true" />
                {entry.label}
              </span>
            ))}
          </div>

          {notEnoughPoints ? (
            <div className="market-history-chart__empty">
              <strong>{formatPercent(latestPoint?.marketProbability ?? null)}</strong>
              <p>Not enough snapshots yet to render a line history. Capture at least one more snapshot to see the market trend.</p>
            </div>
          ) : (
            <>
              <div className="market-history-chart__surface">
                <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Market history chart">
                  {Y_AXIS_TICKS.map((tick) => {
                    const y = domain.maxY - tick * (domain.maxY - domain.minY);
                    return (
                      <g key={tick}>
                        <line x1={domain.minX} y1={y} x2={domain.maxX} y2={y} className="market-history-chart__grid-line" />
                        <text x={domain.minX - 10} y={y + 4} textAnchor="end" className="market-history-chart__axis-label">
                          {formatPercent(tick)}
                        </text>
                      </g>
                    );
                  })}

                  {series.map((entry) => (
                    <path
                      key={entry.key}
                      d={buildLinePath(chartPoints.map((point) => ({ x: point.x, y: point.yValues[entry.key] })))}
                      fill="none"
                      stroke={entry.color}
                      strokeWidth={entry.strokeWidth}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  ))}

                  {chartPoints.map((point, index) => (
                    <g key={point.id}>
                      <line
                        x1={point.x}
                        y1={domain.minY}
                        x2={point.x}
                        y2={domain.maxY}
                        className={hoveredIndex === index ? 'market-history-chart__cursor-line is-visible' : 'market-history-chart__cursor-line'}
                      />
                      <rect
                        x={point.x - 10}
                        y={domain.minY}
                        width={20}
                        height={domain.maxY - domain.minY}
                        fill="transparent"
                        onMouseEnter={() => setHoveredIndex(index)}
                        onMouseLeave={() => setHoveredIndex(null)}
                      />
                      {series.map((entry) => {
                        const y = point.yValues[entry.key];
                        if (y === null) {
                          return null;
                        }

                        return (
                          <circle
                            key={entry.key}
                            cx={point.x}
                            cy={y}
                            r={hoveredIndex === index ? 5 : 3.5}
                            fill={entry.color}
                            stroke="#04111d"
                            strokeWidth={1.5}
                          />
                        );
                      })}
                    </g>
                  ))}

                  {xAxisLabels.map((point) => (
                    <text key={point.id} x={point.x} y={CHART_HEIGHT - 16} textAnchor="middle" className="market-history-chart__axis-label">
                      {new Intl.DateTimeFormat('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      }).format(new Date(point.capturedAt))}
                    </text>
                  ))}
                </svg>

                {activeTooltipPoint ? (
                  <div className="market-history-chart__tooltip">
                    <span>{activeTooltipPoint.capturedAtLabel}</span>
                    <strong>{formatPercent(activeTooltipPoint.marketProbability)}</strong>
                    {activeTooltipPoint.yesPrice !== null ? <small>YES {formatPercent(activeTooltipPoint.yesPrice)}</small> : null}
                    {activeTooltipPoint.noPrice !== null ? <small>NO {formatPercent(activeTooltipPoint.noPrice)}</small> : null}
                  </div>
                ) : null}
              </div>

              <p className="market-history-chart__footnote">
                The chart uses `recent_snapshots` from `GET /api/markets/&lt;id&gt;/` and keeps the Y axis normalized from 0% to 100% so probability and YES/NO prices stay easy to compare.
              </p>
            </>
          )}
        </div>
      ) : null}
    </SectionCard>
  );
}
