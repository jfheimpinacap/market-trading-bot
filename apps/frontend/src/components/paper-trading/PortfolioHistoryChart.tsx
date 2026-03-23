import { useMemo, useState } from 'react';
import type { PaperPortfolioSnapshot } from '../../types/paperTrading';
import { formatPaperCurrency } from './utils';
import {
  getPortfolioHistoryValueRange,
  hasPortfolioHistorySeries,
  mapSnapshotsToPortfolioHistoryPoints,
} from './portfolioHistory';

type PortfolioHistoryChartProps = {
  snapshots: PaperPortfolioSnapshot[];
  currency: string;
  isLoading?: boolean;
  error?: string | null;
};

type PortfolioHistorySeriesKey = 'equity' | 'cashBalance' | 'totalPnl';

type SeriesConfig = {
  key: PortfolioHistorySeriesKey;
  label: string;
  color: string;
  strokeWidth: number;
};

const CHART_WIDTH = 760;
const CHART_HEIGHT = 320;
const PADDING = { top: 20, right: 20, bottom: 48, left: 72 };
const SERIES: SeriesConfig[] = [
  { key: 'equity', label: 'Equity', color: '#284bce', strokeWidth: 3 },
  { key: 'cashBalance', label: 'Cash balance', color: '#0f9f6e', strokeWidth: 2.5 },
  { key: 'totalPnl', label: 'Total PnL', color: '#b7791f', strokeWidth: 2 },
];
const Y_AXIS_TICKS = 4;

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

export function PortfolioHistoryChart({
  snapshots,
  currency,
  isLoading = false,
  error = null,
}: PortfolioHistoryChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const historyPoints = useMemo(() => mapSnapshotsToPortfolioHistoryPoints(snapshots), [snapshots]);
  const latestPoint = historyPoints[historyPoints.length - 1] ?? null;
  const firstPoint = historyPoints[0] ?? null;
  const valueRange = useMemo(() => getPortfolioHistoryValueRange(historyPoints), [historyPoints]);
  const series = useMemo(
    () => SERIES.filter((entry) => entry.key === 'equity' || hasPortfolioHistorySeries(historyPoints, entry.key)),
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
      if (value === null || valueRange === null) {
        return null;
      }

      const normalized = (value - valueRange.min) / Math.max(valueRange.max - valueRange.min, 1);
      return domain.maxY - normalized * (domain.maxY - domain.minY);
    };

    return {
      ...point,
      x,
      yValues: {
        equity: projectY(point.equity),
        cashBalance: projectY(point.cashBalance),
        totalPnl: projectY(point.totalPnl),
      },
    };
  });

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

  const yAxisTicks = valueRange === null
    ? []
    : Array.from({ length: Y_AXIS_TICKS + 1 }, (_, index) => {
      const ratio = index / Y_AXIS_TICKS;
      const value = valueRange.max - ratio * (valueRange.max - valueRange.min);
      const y = domain.minY + ratio * (domain.maxY - domain.minY);
      return { value, y };
    });

  const notEnoughPoints = historyPoints.length < 2;

  if (isLoading) {
    return <p className="portfolio-history-state">Loading portfolio history from paper snapshots…</p>;
  }

  if (error) {
    return <p className="portfolio-history-state portfolio-history-state--error">Could not load portfolio history. {error}</p>;
  }

  if (historyPoints.length === 0) {
    return (
      <div className="portfolio-history-state-card">
        <strong>No snapshots captured yet</strong>
        <p>Run revalue or execute paper trades to build portfolio history for the demo account.</p>
      </div>
    );
  }

  return (
    <div className="portfolio-history-chart">
      <div className="portfolio-history-chart__summary-grid">
        <article className="portfolio-history-chart__summary-card">
          <span>Snapshots</span>
          <strong>{historyPoints.length}</strong>
          <small>{firstPoint ? `Since ${firstPoint.capturedAtLabel}` : 'Waiting for first capture.'}</small>
        </article>
        <article className="portfolio-history-chart__summary-card">
          <span>Latest equity</span>
          <strong>{formatPaperCurrency(latestPoint?.equity ?? null, currency)}</strong>
          <small>{latestPoint ? latestPoint.capturedAtLabel : '—'}</small>
        </article>
        <article className="portfolio-history-chart__summary-card">
          <span>Latest total PnL</span>
          <strong>{formatPaperCurrency(latestPoint?.totalPnl ?? null, currency)}</strong>
          <small>{latestPoint ? `${latestPoint.openPositionsCount} open positions` : '—'}</small>
        </article>
      </div>

      <div className="portfolio-history-chart__legend">
        {series.map((entry) => (
          <span key={entry.key} className="portfolio-history-chart__legend-item">
            <i style={{ backgroundColor: entry.color }} aria-hidden="true" />
            {entry.label}
          </span>
        ))}
      </div>

      {notEnoughPoints ? (
        <div className="portfolio-history-chart__empty">
          <strong>{formatPaperCurrency(latestPoint?.equity ?? null, currency)}</strong>
          <p>Not enough portfolio snapshots yet to render history. Run revalue or execute another paper trade to capture at least one more point.</p>
        </div>
      ) : (
        <>
          <div className="portfolio-history-chart__surface">
            <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img" aria-label="Portfolio history chart">
              {yAxisTicks.map((tick) => (
                <g key={`${tick.value}-${tick.y}`}>
                  <line x1={domain.minX} y1={tick.y} x2={domain.maxX} y2={tick.y} className="portfolio-history-chart__grid-line" />
                  <text x={domain.minX - 12} y={tick.y + 4} textAnchor="end" className="portfolio-history-chart__axis-label">
                    {formatPaperCurrency(tick.value, currency, { notation: 'compact', maximumFractionDigits: 1 })}
                  </text>
                </g>
              ))}

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
                    className={hoveredIndex === index ? 'portfolio-history-chart__cursor-line is-visible' : 'portfolio-history-chart__cursor-line'}
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
                        stroke="#ffffff"
                        strokeWidth={2}
                      />
                    );
                  })}
                </g>
              ))}

              {xAxisLabels.map((point) => (
                <text key={point.id} x={point.x} y={CHART_HEIGHT - 16} textAnchor="middle" className="portfolio-history-chart__axis-label">
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
              <div className="portfolio-history-chart__tooltip">
                <span>{activeTooltipPoint.capturedAtLabel}</span>
                <strong>{formatPaperCurrency(activeTooltipPoint.equity, currency)}</strong>
                <small>Cash {formatPaperCurrency(activeTooltipPoint.cashBalance, currency)}</small>
                <small>Total PnL {formatPaperCurrency(activeTooltipPoint.totalPnl, currency)}</small>
              </div>
            ) : null}
          </div>

          <p className="portfolio-history-chart__footnote">
            The chart uses `GET /api/paper/snapshots/` and plots equity as the primary series, with cash balance and total PnL overlays when snapshots contain those values.
          </p>
        </>
      )}
    </div>
  );
}
