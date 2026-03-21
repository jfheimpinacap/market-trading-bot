import { AgentsPage } from '../pages/AgentsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { MarketsPage } from '../pages/MarketsPage';
import { PortfolioPage } from '../pages/PortfolioPage';
import { PostMortemPage } from '../pages/PostMortemPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SignalsPage } from '../pages/SignalsPage';
import { SystemPage } from '../pages/SystemPage';
import type { NavRoute } from '../types/system';

export type AppRoute = NavRoute & {
  component: () => JSX.Element;
};

export const appRoutes: AppRoute[] = [
  {
    label: 'Dashboard',
    path: '/',
    description: 'Operational overview of the local platform scaffold.',
    component: DashboardPage,
  },
  {
    label: 'Markets',
    path: '/markets',
    description: 'Future market explorer, watchlists, and discovery workflows.',
    component: MarketsPage,
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
    description: 'Paper positions, exposure monitoring, and PnL placeholders.',
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
  return appRoutes.find((route) => route.path === pathname);
}
