import { InfoCard } from '../components/InfoCard';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { API_BASE_URL, FRONTEND_RUNTIME } from '../lib/config';

const futureProviders = ['Kalshi adapter', 'Polymarket adapter', 'Manual local datasets'];
const integrationNotes = [
  'Settings remain read-only in this phase to avoid premature complexity.',
  'The app is optimized for local development and personal use only.',
  'Future iterations can promote these placeholders into forms and persisted preferences.',
];

export function SettingsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        description="Local-first configuration overview for the frontend application and future integrations."
      />

      <section className="content-grid content-grid--three-columns">
        <InfoCard title="API base URL" description={API_BASE_URL} eyebrow="Current configuration" />
        <InfoCard title="Execution mode" description={FRONTEND_RUNTIME} eyebrow="Runtime" />
        <InfoCard
          title="Future integrations"
          description="Provider adapters, Redis-backed services, and orchestration settings will be introduced here later."
          eyebrow="Planned"
        />
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          title="Future providers"
          description="Reserved space for local provider credentials, feature toggles, and adapter diagnostics."
        >
          <ul className="bullet-list">
            {futureProviders.map((provider) => (
              <li key={provider}>{provider}</li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard
          title="Configuration notes"
          description="These notes clarify what is intentionally scaffolded now versus what comes later."
        >
          <ul className="bullet-list">
            {integrationNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </SectionCard>
      </section>
    </div>
  );
}
