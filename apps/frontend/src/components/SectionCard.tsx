import type { PropsWithChildren, ReactNode } from 'react';

type SectionCardProps = PropsWithChildren<{
  title: string;
  description?: string;
  eyebrow?: string;
  aside?: ReactNode;
}>;

export function SectionCard({ title, description, eyebrow, aside, children }: SectionCardProps) {
  return (
    <section className="panel section-card">
      <div className="section-card__header">
        <div>
          {eyebrow ? <p className="section-label">{eyebrow}</p> : null}
          <h2>{title}</h2>
          {description ? <p className="section-card__description">{description}</p> : null}
        </div>
        {aside ? <div className="section-card__aside">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}
