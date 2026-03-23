import type { WorkflowStatusItem } from '../../types/demoFlow';
import { navigate } from '../../lib/router';
import type { MouseEvent } from 'react';

type WorkflowStatusPanelProps = {
  title: string;
  description: string;
  items: WorkflowStatusItem[];
};

function handleNavigate(event: MouseEvent<HTMLAnchorElement>, href: string) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(href);
}

export function WorkflowStatusPanel({ title, description, items }: WorkflowStatusPanelProps) {
  return (
    <section className="panel workflow-status-panel">
      <div className="workflow-status-panel__header">
        <div>
          <p className="section-label">Workflow overview</p>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      <div className="workflow-status-grid">
        {items.map((item) => (
          <article key={item.label} className={`workflow-status-card workflow-status-card--${item.tone ?? 'neutral'}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <p>{item.helperText}</p>
            {item.href ? (
              <a href={item.href} className="workflow-status-card__link" onClick={(event) => handleNavigate(event, item.href!)}>
                {item.linkLabel ?? 'Open'}
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
