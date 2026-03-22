import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { DashboardQuickLink } from '../../types/dashboard';
import { StatusBadge } from './StatusBadge';

type QuickLinksPanelProps = {
  links: DashboardQuickLink[];
};

export function QuickLinksPanel({ links }: QuickLinksPanelProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>, path: string) {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    event.preventDefault();
    navigate(path);
  }

  return (
    <div className="dashboard-link-grid">
      {links.map((link) => (
        <a key={link.path} className="dashboard-link-card" href={link.path} onClick={(event) => handleClick(event, link.path)}>
          <div className="dashboard-link-card__header">
            <h3>{link.title}</h3>
            <StatusBadge tone={link.availability === 'live' ? 'ready' : 'pending'}>
              {link.availability === 'live' ? 'Ready' : 'Planned'}
            </StatusBadge>
          </div>
          <p>{link.description}</p>
          <span className="dashboard-link-card__cta">Open module →</span>
        </a>
      ))}
    </div>
  );
}
