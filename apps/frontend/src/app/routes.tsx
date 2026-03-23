import { AgentsPage } from '../pages/AgentsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { MarketDetailPage } from '../pages/MarketDetailPage';
import { MarketsPage } from '../pages/MarketsPage';
import { PortfolioPage } from '../pages/PortfolioPage';
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
    description: 'Signal generation workspace for future decision support.',
    component: SignalsPage,
  },
  {
    label: 'Agents',
    path: '/agents',
    description: 'Agent orchestration, automation status, and run visibility.',
    component: AgentsPage,
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
    description: 'Retrospectives, incident reviews, and learning loops.',
    component: PostMortemPage,
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
