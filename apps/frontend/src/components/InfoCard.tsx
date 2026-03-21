import type { ReactNode } from 'react';

type InfoCardProps = {
  title: string;
  description: string;
  eyebrow?: string;
  footer?: ReactNode;
};

export function InfoCard({ title, description, eyebrow, footer }: InfoCardProps) {
  return (
    <article className="panel info-card">
      {eyebrow ? <p className="section-label">{eyebrow}</p> : null}
      <h3>{title}</h3>
      <p>{description}</p>
      {footer ? <div className="info-card__footer">{footer}</div> : null}
    </article>
  );
}
