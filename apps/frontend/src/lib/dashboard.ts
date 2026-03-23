import { API_BASE_URL, FRONTEND_RUNTIME } from './config';
import type { DashboardModuleStatus, DashboardQuickLink } from '../types/dashboard';

export const dashboardQuickLinks: DashboardQuickLink[] = [
  {
    title: 'Markets',
    description: 'Open the live demo catalog, apply filters, and drill into market detail pages.',
    path: '/markets',
    availability: 'live',
  },
  {
    title: 'System',
    description: 'Review backend connectivity, environment details, and shared health state.',
    path: '/system',
    availability: 'live',
  },
  {
    title: 'Settings',
    description: 'Keep local-first configuration notes and future environment controls in one place.',
    path: '/settings',
    availability: 'live',
  },
  {
    title: 'Agents',
    description: 'Reserved for orchestration summaries, schedules, and agent run visibility.',
    path: '/agents',
    availability: 'placeholder',
  },
  {
    title: 'Portfolio',
    description: 'Inspect paper balances, trade history, positions, and review links for executed trades.',
    path: '/portfolio',
    availability: 'live',
  },
  {
    title: 'Post-Mortem',
    description: 'Inspect demo trade reviews, outcome counts, and simple lessons from the local review engine.',
    path: '/postmortem',
    availability: 'live',
  },
];

export const dashboardModules: DashboardModuleStatus[] = [
  {
    name: 'Health API',
    summary: 'Shared healthcheck integration is already wired into Dashboard and System views.',
    status: 'ready',
  },
  {
    name: 'Markets catalog',
    summary: 'Read-only market discovery with filters, detail view, and seeded demo records is available.',
    status: 'ready',
  },
  {
    name: 'Markets detail',
    summary: 'Rules, snapshots, metadata, and navigation from the catalog are implemented.',
    status: 'ready',
  },
  {
    name: 'Dashboard integration',
    summary: 'The landing page now consumes live backend health and market summary data.',
    status: 'ready',
  },
  {
    name: 'Providers real sync',
    summary: 'External provider ingestion is intentionally deferred until after the local demo workflow.',
    status: 'pending',
  },
  {
    name: 'Paper trading',
    summary: 'Execution workflows, positions, PnL, and portfolio history are available in the local demo account.',
    status: 'ready',
  },
  {
    name: 'Risk engine',
    summary: 'The demo risk guard is integrated into the trade flow before paper execution.',
    status: 'ready',
  },
  {
    name: 'Post-mortem',
    summary: 'Trade reviews, outcome summaries, and linked retrospective detail are now available for paper trades.',
    status: 'ready',
  },
];

export const nextProjectSteps = [
  'Extend the System panel with provider diagnostics, worker visibility, and richer local service checks.',
  'Keep expanding the seeded demo catalog so the dashboard and Markets module feel realistic during development.',
  'Expand the post-mortem heuristics with richer execution context and refresh flows once the review loop settles.',
];

export const localEnvironmentHighlights = [
  { label: 'Runtime', value: FRONTEND_RUNTIME },
  { label: 'System mode', value: 'Local demo' },
  { label: 'Backend API', value: API_BASE_URL },
  { label: 'Data source', value: 'Seeded Django demo catalog' },
];
