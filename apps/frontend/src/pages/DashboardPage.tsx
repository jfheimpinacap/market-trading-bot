import { ModuleList } from '../components/ModuleList';
import { StatusCard } from '../components/StatusCard';
import { AppShell } from '../layouts/AppShell';

const statusItems = [
  {
    title: 'Frontend',
    value: 'Ready',
    description: 'React + Vite + TypeScript scaffold prepared for future product modules.',
  },
  {
    title: 'Backend',
    value: 'Ready',
    description: 'Django REST API scaffold with healthcheck and Celery wiring prepared.',
  },
  {
    title: 'Infrastructure',
    value: 'Ready',
    description: 'Docker Compose includes PostgreSQL and Redis for local development.',
  },
];

export function DashboardPage() {
  return (
    <AppShell>
      <section className="dashboard-grid">
        {statusItems.map((item) => (
          <StatusCard key={item.title} title={item.title} value={item.value} description={item.description} />
        ))}
      </section>
      <ModuleList />
    </AppShell>
  );
}
