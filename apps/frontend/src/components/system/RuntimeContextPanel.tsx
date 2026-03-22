import { SectionCard } from '../SectionCard';
import type { SystemRuntimeInfo } from '../../types/system';

type RuntimeContextPanelProps = {
  items: SystemRuntimeInfo[];
};

export function RuntimeContextPanel({ items }: RuntimeContextPanelProps) {
  return (
    <SectionCard
      eyebrow="Runtime context"
      title="Local runtime context"
      description="Static local-first context plus a few runtime values so you can confirm what the frontend is pointing at."
    >
      <dl className="dashboard-key-value-list">
        {items.map((item) => (
          <div key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  );
}
