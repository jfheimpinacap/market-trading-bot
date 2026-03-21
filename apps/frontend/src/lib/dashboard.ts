import type { DashboardModule } from '../types/system';

export const dashboardModules: DashboardModule[] = [
  {
    name: 'Dashboard',
    summary: 'Operational landing page with health, roadmap, and architecture context.',
    status: 'available',
  },
  {
    name: 'Markets',
    summary: 'Future discovery view for market scanning, watchlists, and filters.',
    status: 'planned',
  },
  {
    name: 'Signals',
    summary: 'Future signal workspace for hypotheses, scorecards, and analyst output.',
    status: 'planned',
  },
  {
    name: 'Agents',
    summary: 'Future automation control panel for orchestration and run monitoring.',
    status: 'planned',
  },
  {
    name: 'Portfolio',
    summary: 'Future paper trading exposure, positions, and risk visibility.',
    status: 'planned',
  },
  {
    name: 'Post-Mortem',
    summary: 'Future retrospective area for incident analysis and iteration feedback.',
    status: 'planned',
  },
];

export const architectureLayers = [
  'Frontend app for local navigation, technical visibility, and operator workflows.',
  'Django API layer exposing health and future domain endpoints.',
  'Shared provider and utility libraries isolated inside libs/ for future integrations.',
  'Future services for discovery, probability, risk, execution, and post-mortem analysis.',
];

export const immediateRoadmap = [
  'Expand local UI modules without introducing real trading logic.',
  'Add domain endpoints beyond the healthcheck when contracts are ready.',
  'Prepare placeholder panels for Redis, Celery, agents, and paper trading lifecycle.',
];
