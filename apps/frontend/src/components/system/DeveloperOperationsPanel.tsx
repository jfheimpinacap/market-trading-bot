import { SectionCard } from '../SectionCard';
import type { DeveloperCommandItem } from '../../types/system';

type DeveloperCommandGroup = {
  title: string;
  description: string;
  commands: DeveloperCommandItem[];
};

type DeveloperOperationsPanelProps = {
  groups: DeveloperCommandGroup[];
};

export function DeveloperOperationsPanel({ groups }: DeveloperOperationsPanelProps) {
  return (
    <SectionCard
      eyebrow="How to operate locally"
      title="Developer operations"
      description="These are reference commands only. The UI does not execute backend operations or control the simulation loop."
    >
      <div className="system-command-groups">
        {groups.map((group) => (
          <section key={group.title} className="system-command-group">
            <div>
              <h3>{group.title}</h3>
              <p>{group.description}</p>
            </div>
            <div className="system-command-grid">
              {group.commands.map((item) => (
                <article key={item.command} className="system-command-card">
                  <div className="system-command-card__header">
                    <h4>{item.label}</h4>
                  </div>
                  <p>{item.description}</p>
                  <code>{item.command}</code>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </SectionCard>
  );
}
