import type { ReactNode } from 'react';

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
  eyebrow?: string;
};

export function EmptyState({ title, description, action, eyebrow = 'Planned module' }: EmptyStateProps) {
  return (
    <section className="panel empty-state">
      <div>
        <p className="section-label">{eyebrow}</p>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </section>
  );
}
