import type { DashboardStatCard } from '../../types/dashboard';

type DashboardStatGridProps = {
  stats: DashboardStatCard[];
};

export function DashboardStatGrid({ stats }: DashboardStatGridProps) {
  return (
    <div className="dashboard-stat-grid">
      {stats.map((stat) => (
        <article key={stat.label} className="dashboard-stat-card">
          <span className="dashboard-stat-card__label">{stat.label}</span>
          <strong className="dashboard-stat-card__value">{stat.value}</strong>
          <span className="dashboard-stat-card__helper">{stat.helperText}</span>
        </article>
      ))}
    </div>
  );
}
