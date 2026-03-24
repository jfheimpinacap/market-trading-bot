import type { DashboardModuleStatus, DashboardQuickLink } from '../types/dashboard';
import type { DeveloperCommandItem } from '../types/system';

export const systemQuickLinks: DashboardQuickLink[] = [
  {
    title: 'Dashboard',
    description: 'Return to the local control center and review shared health plus catalog summary cards.',
    path: '/',
    availability: 'live',
  },
  {
    title: 'Automation',
    description: 'Open the demo control center to trigger safe local actions from the UI.',
    path: '/automation',
    availability: 'live',
  },

  {
    title: 'Continuous Demo',
    description: 'Open autonomous continuous loop controls, status, and safety guardrails for paper mode.',
    path: '/continuous-demo',
    availability: 'live',
  },
  {
    title: 'Semi-Auto',
    description: 'Inspect conservative semi-autonomous paper execution with manual approval gates.',
    path: '/semi-auto',
    availability: 'live',
  },
  {
    title: 'Evaluation',
    description: 'Inspect objective benchmark metrics and run-to-run comparisons before increasing autonomy.',
    path: '/evaluation',
    availability: 'live',
  },
  {
    title: 'Markets',
    description: 'Inspect the seeded market catalog, filters, and per-market detail pages.',
    path: '/markets',
    availability: 'live',
  },
  {
    title: 'Settings',
    description: 'Open the local configuration placeholder and keep environment notes in view.',
    path: '/settings',
    availability: 'live',
  },
];

export const systemModuleReadiness: DashboardModuleStatus[] = [
  {
    name: 'Health API',
    summary: 'GET /api/health/ is already wired through the shared health provider and reused by multiple pages.',
    status: 'ready',
  },
  {
    name: 'Markets catalog',
    summary: 'Read-only market discovery and typed services are already available for local inspection.',
    status: 'ready',
  },
  {
    name: 'Market simulation engine',
    summary: 'The backend can generate coherent snapshots locally, and this page now surfaces observable movement indirectly.',
    status: 'ready',
  },
  {
    name: 'Dashboard integration',
    summary: 'The dashboard already consumes shared health and market summary data from the local backend.',
    status: 'ready',
  },
  {
    name: 'System page',
    summary: 'The placeholder has been replaced with a technical panel for runtime context, activity inspection, and local operations.',
    status: 'ready',
  },
  {
    name: 'Real provider sync',
    summary: 'External ingestion remains intentionally deferred while the project stays local-first and demo-driven.',
    status: 'pending',
  },
  {
    name: 'Guided automation',
    summary: 'Automation actions are available as explicit operator controls and feed the continuous demo loop.',
    status: 'ready',
  },
  {
    name: 'Continuous demo loop',
    summary: 'Background/pseudo-background autonomous paper-only cycles are now available with stop/pause/kill controls.',
    status: 'ready',
  },
  {
    name: 'Paper trading',
    summary: 'Execution workflows, orders, positions, and PnL are still outside this milestone.',
    status: 'pending',
  },
  {
    name: 'Risk engine',
    summary: 'Risk controls, scenario checks, and guardrails remain future work.',
    status: 'pending',
  },
  {
    name: 'Post-mortem',
    summary: 'Retrospective analysis and anomaly review remain reserved in navigation but not implemented.',
    status: 'pending',
  },
];

export const developerCommandGroups: Array<{ title: string; description: string; commands: DeveloperCommandItem[] }> = [
  {
    title: 'Backend setup',
    description: 'Prepare the Django app and seed the local demo dataset.',
    commands: [
      {
        label: 'Apply migrations',
        command: 'cd apps/backend && python manage.py migrate',
        description: 'Bring the local database schema up to date before seeding or running the API.',
      },
      {
        label: 'Seed demo markets',
        command: 'cd apps/backend && python manage.py seed_markets_demo',
        description: 'Load the providers, events, markets, and initial snapshots used by the System and Markets pages.',
      },
    ],
  },
  {
    title: 'Simulation',
    description: 'Generate additional movement that the System page can observe through existing endpoints.',
    commands: [
      {
        label: 'Run one tick',
        command: 'cd apps/backend && python manage.py simulate_markets_tick',
        description: 'Create one simulation pass so snapshot counts and market metrics can change after a manual refresh.',
      },
      {
        label: 'Run loop',
        command: 'cd apps/backend && python manage.py simulate_markets_loop',
        description: 'Keep generating local activity in a loop while watching the System page refresh manually.',
      },
    ],
  },
  {
    title: 'Local servers',
    description: 'Start the backend and frontend used by the local-first workspace.',
    commands: [
      {
        label: 'Start Django',
        command: 'cd apps/backend && python manage.py runserver',
        description: 'Serve the health and markets endpoints consumed by Dashboard, Markets, and System.',
      },
      {
        label: 'Start Vite',
        command: 'cd apps/frontend && npm run dev',
        description: 'Launch the frontend shell and open the `/system` route in the browser.',
      },
    ],
  },
];
