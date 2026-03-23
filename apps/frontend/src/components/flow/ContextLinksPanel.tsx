import type { MouseEvent } from 'react';
import { navigate } from '../../lib/router';
import type { ContextLinkItem } from '../../types/demoFlow';

type ContextLinksPanelProps = {
  eyebrow?: string;
  title: string;
  description: string;
  links: ContextLinkItem[];
};

function handleNavigate(event: MouseEvent<HTMLAnchorElement>, href: string) {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
    return;
  }

  event.preventDefault();
  navigate(href);
}

export function ContextLinksPanel({ eyebrow = 'Context links', title, description, links }: ContextLinksPanelProps) {
  return (
    <section className="panel context-links-panel">
      <div>
        <p className="section-label">{eyebrow}</p>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>

      <div className="context-links-grid">
        {links.map((link) => (
          <a
            key={`${link.href}-${link.title}`}
            href={link.href}
            className={`context-link-card context-link-card--${link.tone ?? 'neutral'}`}
            onClick={(event) => handleNavigate(event, link.href)}
          >
            <strong>{link.title}</strong>
            <span>{link.description}</span>
            <em>{link.actionLabel} →</em>
          </a>
        ))}
      </div>
    </section>
  );
}
