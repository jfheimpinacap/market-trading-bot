import { API_BASE_URL, FRONTEND_RUNTIME } from './config';
import type { DashboardModuleStatus, DashboardQuickLink } from '../types/dashboard';

export const dashboardQuickLinks: DashboardQuickLink[] = [
  {
    title: 'Markets',
    description: 'Start in the catalog, inspect active contracts, and jump into the operational market detail flow.',
    path: '/markets',
    availability: 'live',
  },
  {
    title: 'Signals',
    description: 'Review demo opportunities, then open the related market or continue toward trade evaluation.',
    path: '/signals',
    availability: 'live',
  },
  {
    title: 'Proposals',
    description: 'Open the trade proposal inbox and continue into market detail before a demo paper trade.',
    path: '/proposals',
    availability: 'live',
  },
  {
    title: 'Automation',
    description: 'Use guided demo controls to move the local system forward without touching the terminal.',
    path: '/automation',
    availability: 'live',
  },

  {
    title: 'Real Ops',
    description: 'Evaluate and run autonomous paper-only cycles on eligible real read-only markets with conservative scope controls.',
    path: '/real-ops',
    availability: 'live',
  },
  {
    title: 'Continuous Demo',
    description: 'Run a continuous autonomous paper-only loop with start/pause/resume/stop and cycle audit traces.',
    path: '/continuous-demo',
    availability: 'live',
  },
  {
    title: 'Allocation',
    description: 'Prioritize and size competing proposals with conservative portfolio-aware caps before paper execution.',
    path: '/allocation',
    availability: 'live',
  },
  {
    title: 'Semi-Auto',
    description: 'Run evaluate-only or conservative paper-only semi-auto cycles with explicit pending approvals.',
    path: '/semi-auto',
    availability: 'live',
  },
  {
    title: 'Portfolio',
    description: 'Check paper balances, positions, trade history, and which executions already have reviews.',
    path: '/portfolio',
    availability: 'live',
  },
  {
    title: 'Post-Mortem',
    description: 'Close the loop with demo trade reviews, lessons learned, and links back to markets and portfolio.',
    path: '/postmortem',
    availability: 'live',
  },
  {
    title: 'Evaluation',
    description: 'Review benchmark snapshots, run comparisons, and objective paper/demo system performance metrics.',
    path: '/evaluation',
    availability: 'live',
  },
  {
    title: 'Safety',
    description: 'Monitor operational guardrails, cooldown state, kill switch, and safety events.',
    path: '/safety',
    availability: 'live',
  },
  {
    title: 'System',
    description: 'Verify the backend, runtime context, and local demo health before exploring the rest of the workflow.',
    path: '/system',
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
    name: 'Signals workspace',
    summary: 'Mock-agent signals now connect directly to market detail, portfolio context, and review follow-ups.',
    status: 'ready',
  },
  {
    name: 'Paper trading',
    summary: 'Execution workflows, positions, PnL, and portfolio history are available in the local demo account.',
    status: 'ready',
  },
  {
    name: 'Proposal engine',
    summary: 'Demo proposals now bridge signals, risk, policy, and market-level execution decisions.',
    status: 'ready',
  },
  {
    name: 'Risk engine',
    summary: 'The demo risk guard is integrated into the trade flow before paper execution.',
    status: 'ready',
  },
  {
    name: 'Automation demo',
    summary: 'Guided UI controls can now trigger safe local demo actions and a traceable full cycle.',
    status: 'ready',
  },
  {
    name: 'Continuous autonomous loop',
    summary: 'A controlled background loop can now run start/pause/resume/stop cycles in paper-only mode.',
    status: 'ready',
  },
  {
    name: 'Post-mortem',
    summary: 'Trade reviews, outcome summaries, and linked retrospective detail are available for paper trades.',
    status: 'ready',
  },
  {
    name: 'Providers real sync',
    summary: 'External provider ingestion is intentionally deferred until after the local demo workflow.',
    status: 'pending',
  },
];

export const nextProjectSteps = [
  'Keep improving the demo workflow links so Signals, Market detail, Portfolio, and Post-mortem read like one operator journey.',
  'Expand the seeded demo catalog so the dashboard and market detail pages feel richer during local evaluation.',
  'Deepen the post-mortem heuristics only after the current manual refresh and navigation loop feels stable.',
];

export const localEnvironmentHighlights = [
  { label: 'Runtime', value: FRONTEND_RUNTIME },
  { label: 'System mode', value: 'Local demo' },
  { label: 'Backend API', value: API_BASE_URL },
  { label: 'Data source', value: 'Seeded Django demo catalog' },
];
