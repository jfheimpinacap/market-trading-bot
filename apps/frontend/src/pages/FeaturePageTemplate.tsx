import { EmptyState } from '../components/EmptyState';
import { InfoCard } from '../components/InfoCard';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';

type FeaturePageTemplateProps = {
  title: string;
  eyebrow: string;
  description: string;
  currentStatus: string;
  futureModule: string;
  nextSteps: string[];
  notes: string[];
};

export function FeaturePageTemplate({
  title,
  eyebrow,
  description,
  currentStatus,
  futureModule,
  nextSteps,
  notes,
}: FeaturePageTemplateProps) {
  return (
    <div className="page-stack">
      <PageHeader title={title} description={description} eyebrow={eyebrow} />

      <section className="content-grid content-grid--two-columns">
        <InfoCard title="Current stage" description={currentStatus} eyebrow="Status" />
        <InfoCard title="Future module" description={futureModule} eyebrow="Planned scope" />
      </section>

      <SectionCard
        title="What will live here"
        description="Each section is already framed so future iterations can add behavior without redesigning the app shell."
      >
        <div className="bullet-columns">
          <div>
            <h3>Next implementation slices</h3>
            <ul className="bullet-list">
              {nextSteps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3>Notes for later stages</h3>
            <ul className="bullet-list">
              {notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        </div>
      </SectionCard>

      <EmptyState
        title={`${title} module scaffolded`}
        description="The visual structure is in place, but business logic, live data, and advanced controls remain intentionally out of scope for this phase."
      />
    </div>
  );
}
