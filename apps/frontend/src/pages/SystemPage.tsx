import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusCard } from '../components/StatusCard';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { API_BASE_URL } from '../lib/config';

function booleanSummary(value: boolean | undefined) {
  return value ? 'Yes' : 'No';
}

export function SystemPage() {
  const health = useSystemHealth();

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Technical panel"
        title="System"
        description="Technical overview of the frontend runtime, backend connectivity, and planned local services."
        actions={
          <button className="secondary-button" type="button" onClick={() => void health.refresh()}>
            Refresh health
          </button>
        }
      />

      <section className="content-grid content-grid--two-columns">
        <StatusCard
          title="Frontend"
          status="online"
          description="The frontend shell is loaded and rendering the local application layout successfully."
          details={[
            { label: 'Status', value: 'Running in browser' },
            { label: 'Mode', value: 'Local development' },
            { label: 'Navigation', value: 'Ready' },
          ]}
        />
        <StatusCard
          title="Backend"
          status={health.backendStatus}
          description={
            health.isError
              ? health.error ?? 'Backend health is currently unavailable.'
              : 'Shared health state is reused from the dashboard to keep status handling consistent.'
          }
          details={[
            { label: 'Configured endpoint', value: `${API_BASE_URL}/api/health/` },
            { label: 'Environment', value: health.data?.environment ?? 'Unavailable' },
            { label: 'Database configured', value: booleanSummary(health.data?.database_configured) },
            { label: 'Redis configured', value: booleanSummary(health.data?.redis_configured) },
          ]}
        />
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          title="Health details"
          description="This page shares the same local healthcheck result used in the dashboard."
        >
          <ul className="bullet-list">
            <li>Frontend status: online.</li>
            <li>Backend status: {health.backendStatus}.</li>
            <li>Configured endpoint: {API_BASE_URL}/api/health/.</li>
            <li>Environment from backend: {health.data?.environment ?? 'Unavailable'}.</li>
            <li>Last checked: {health.lastCheckedAt ?? 'Pending'}.</li>
          </ul>
        </SectionCard>

        <SectionCard
          title="Future system integrations"
          description="These capabilities are intentionally deferred, but the technical panel reserves space for them now."
        >
          <ul className="bullet-list">
            <li>Redis and Celery worker visibility.</li>
            <li>Provider connectivity diagnostics.</li>
            <li>Agent orchestration state.</li>
            <li>Paper trading services and local execution telemetry.</li>
          </ul>
        </SectionCard>
      </section>
    </div>
  );
}
