import { DashboardStatGrid } from '../dashboard/DashboardStatGrid';
import { formatDateTime } from '../markets/utils';
import type { DashboardStatCard } from '../../types/dashboard';
import type { SignalSummary } from '../../types/signals';

type SignalsSummaryCardsProps = {
  summary: SignalSummary;
};

export function SignalsSummaryCards({ summary }: SignalsSummaryCardsProps) {
  const stats: DashboardStatCard[] = [
    {
      label: 'Signals',
      value: String(summary.total_signals),
      helperText: 'Total demo signals currently stored for the local market catalog.',
    },
    {
      label: 'Actionable',
      value: String(summary.actionable_signals),
      helperText: 'Signals that survived the demo spread, activity, and status checks.',
    },
    {
      label: 'Covered markets',
      value: String(summary.markets_with_signals),
      helperText: 'Markets with at least one demo signal in the current local queue.',
    },
    {
      label: 'Bullish / bearish',
      value: `${summary.bullish_signals} / ${summary.bearish_signals}`,
      helperText: 'Direction mix produced by the current mock heuristics.',
    },
    {
      label: 'Active agents',
      value: String(summary.active_agents),
      helperText: 'Mock agents currently available to explain or classify signals.',
    },
    {
      label: 'Latest run',
      value: summary.latest_run ? `#${summary.latest_run.id}` : 'None',
      helperText: summary.latest_signal_at
        ? `Latest signal timestamp: ${formatDateTime(summary.latest_signal_at)}.`
        : 'No demo signals have been generated yet.',
    },
  ];

  return <DashboardStatGrid stats={stats} />;
}
