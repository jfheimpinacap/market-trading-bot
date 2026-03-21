import type { ReactNode } from 'react';
import type { SystemStatus } from '../types/system';

type StatusDetail = {
  label: string;
  value: ReactNode;
};

type StatusCardProps = {
  title: string;
  status: SystemStatus;
  description: string;
  details?: StatusDetail[];
};

const statusLabelMap: Record<SystemStatus, string> = {
  loading: 'Loading',
  online: 'Online',
  offline: 'Offline',
  degraded: 'Degraded',
};

export function StatusCard({ title, status, description, details = [] }: StatusCardProps) {
  return (
    <article className={`panel status-card status-card--${status}`}>
      <div className="status-card__header">
        <div>
          <p className="section-label">System status</p>
          <h3>{title}</h3>
        </div>
        <span className={`status-badge status-badge--${status}`}>{statusLabelMap[status]}</span>
      </div>
      <p>{description}</p>
      {details.length > 0 ? (
        <dl className="status-card__details">
          {details.map((detail) => (
            <div key={detail.label}>
              <dt>{detail.label}</dt>
              <dd>{detail.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </article>
  );
}
