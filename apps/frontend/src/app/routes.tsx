import { AgentsPage } from '../pages/AgentsPage';
import { AutomationPage } from '../pages/AutomationPage';
import { DashboardPage } from '../pages/DashboardPage';
import { MarketDetailPage } from '../pages/MarketDetailPage';
import { MarketsPage } from '../pages/MarketsPage';
import { PortfolioPage } from '../pages/PortfolioPage';
import { ProposalsPage } from '../pages/ProposalsPage';
import { PostMortemPage } from '../pages/PostMortemPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SignalsPage } from '../pages/SignalsPage';
import { SystemPage } from '../pages/SystemPage';
import type { NavRoute } from '../types/system';

export type AppRoute = NavRoute & {
  component: () => JSX.Element;
  match?: (pathname: string) => boolean;
};

export const appRoutes: AppRoute[] = [
  {
    label: 'Dashboard',
    path: '/',
    description: 'Operational overview of the local platform scaffold.',
    component: DashboardPage,
    match: (pathname) => pathname === '/',
  },
  {
    label: 'Markets',
    path: '/markets',
    description: 'Browse demo market data, filters, summary metrics, and focused market detail views.',
    component: MarketsPage,
    match: (pathname) => pathname === '/markets',
  },
  {
    label: 'Market detail',
    path: '/markets/:marketId',
    description: 'Inspect one market, including rules, recent snapshots, and operational metadata.',
    component: MarketDetailPage,
    match: (pathname) => /^\/markets\/[^/]+\/?$/.test(pathname),
  },
  {
    label: 'Signals',
    path: '/signals',
    description: 'Demo signals workspace for mock-agent insights, scored opportunities, and local heuristics.',
    component: SignalsPage,
  },
  {
    label: 'Proposals',
    path: '/proposals',
    description: 'Demo trade proposal inbox with generated thesis, suggested sizing, and approval context before paper execution.',
    component: ProposalsPage,
  },
  {
    label: 'Agents',
    path: '/agents',
    description: 'Agent orchestration, automation status, and run visibility.',
    component: AgentsPage,
  },
  {
    label: 'Automation',
    path: '/automation',
    description: 'Guided demo controls for simulation, signals, portfolio revalue, and review refresh runs.',
    component: AutomationPage,
  },
  {
    label: 'Portfolio',
    path: '/portfolio',
    description: 'Paper trading portfolio summary with account metrics, positions, trades, snapshots, and manual revaluation.',
    component: PortfolioPage,
  },
  {
    label: 'Post-Mortem',
    path: '/postmortem',
    description: 'Retrospectives, trade reviews, and learning loops for paper trades.',
    component: PostMortemPage,
    match: (pathname) => /^\/postmortem(\/[^/]+)?\/?$/.test(pathname),
  },
  {
    label: 'Settings',
    path: '/settings',
    description: 'Local-first application configuration and environment notes.',
    component: SettingsPage,
  },
  {
    label: 'System',
    path: '/system',
    description: 'Technical health, dependencies, and platform connectivity.',
    component: SystemPage,
  },
];

export function getRouteByPath(pathname: string) {
  return appRoutes.find((route) => (route.match ? route.match(pathname) : route.path === pathname));
}
