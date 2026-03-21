import { InfoCard } from '../components/InfoCard';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusCard } from '../components/StatusCard';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { API_BASE_URL, PROJECT_NAME } from '../lib/config';
import { architectureLayers, dashboardModules, immediateRoadmap } from '../lib/dashboard';

function formatBooleanFlag(value: boolean | undefined) {
  return value ? 'Configured' : 'Not configured yet';
}

export function DashboardPage() {
  const health = useSystemHealth();

  const backendDescription = health.isLoading
    ? 'Checking the local backend health endpoint.'
    : health.isError
      ? 'The frontend could not reach the backend health endpoint. Verify that Django is running locally.'
      : 'Backend healthcheck loaded successfully from the local Django API.';

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Platform overview"
        title={PROJECT_NAME}
        description="Local-first dashboard scaffold prepared for future research, signals, agents, paper trading, and post-mortem workflows."
      />

      <section className="content-grid content-grid--three-columns">
        <StatusCard
          title="Frontend workspace"
          status="online"
          description="Vite + React + TypeScript frontend scaffold is ready for iterative feature delivery."
          details={[
            { label: 'Runtime', value: 'Local' },
            { label: 'Layout', value: 'Dashboard shell active' },
            { label: 'Routing', value: 'Multi-page navigation ready' },
          ]}
        />
        <StatusCard
          title="Backend connection"
          status={health.backendStatus}
          description={backendDescription}
          details={[
            { label: 'Endpoint', value: `${API_BASE_URL}/api/health/` },
            { label: 'Environment', value: health.data?.environment ?? 'Unavailable' },
            { label: 'Database', value: formatBooleanFlag(health.data?.database_configured) },
            { label: 'Redis', value: formatBooleanFlag(health.data?.redis_configured) },
          ]}
        />
        <StatusCard
          title="Project stage"
          status="degraded"
          description="The platform foundation is ready, while domain logic remains intentionally deferred to later milestones."
          details={[
            { label: 'Trading logic', value: 'Not implemented' },
            { label: 'Authentication', value: 'Not implemented' },
            { label: 'Providers', value: 'Planned' },
          ]}
        />
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          title="Modules available or planned"
          description="The navigation already mirrors the intended product domains so the frontend can scale without a structural rewrite."
        >
          <ul className="module-grid">
            {dashboardModules.map((module) => (
              <li key={module.name} className="module-grid__item">
                <div>
                  <h3>{module.name}</h3>
                  <p>{module.summary}</p>
                </div>
                <span className={`pill pill--${module.status}`}>{module.status}</span>
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard
          title="Immediate roadmap"
          description="This phase focuses on a clean shell, reliable health visibility, and future-friendly boundaries."
        >
          <ul className="bullet-list">
            {immediateRoadmap.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </SectionCard>
      </section>

      <section className="content-grid content-grid--two-columns">
        <InfoCard
          eyebrow="System summary"
          title="Current platform posture"
          description="The monorepo already separates frontend, backend, services, libraries, and infrastructure so future modules can be introduced with minimal churn."
          footer={<span className="muted-text">This dashboard is intentionally simple and local-only in this iteration.</span>}
        />
        <SectionCard
          eyebrow="Architecture"
          title="High-level architecture"
          description="The frontend now acts as a stable entry point for technical visibility and future operational workflows."
        >
          <ul className="bullet-list">
            {architectureLayers.map((layer) => (
              <li key={layer}>{layer}</li>
            ))}
          </ul>
        </SectionCard>
      </section>
    </div>
  );
}
