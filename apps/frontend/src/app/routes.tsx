import { AgentsPage } from '../pages/AgentsPage';
import { AutomationPage } from '../pages/AutomationPage';
import { AlertsPage } from '../pages/AlertsPage';
import { NotificationsPage } from '../pages/NotificationsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { EvaluationPage } from '../pages/EvaluationPage';
import { ExperimentsPage } from '../pages/ExperimentsPage';
import { ReadinessPage } from '../pages/ReadinessPage';
import { RuntimePage } from '../pages/RuntimePage';
import { ReplayPage } from '../pages/ReplayPage';
import { LearningPage } from '../pages/LearningPage';
import { RealOpsPage } from '../pages/RealOpsPage';
import { ContinuousDemoPage } from '../pages/ContinuousDemoPage';
import { AllocationPage } from '../pages/AllocationPage';
import { MarketDetailPage } from '../pages/MarketDetailPage';
import { OperatorQueuePage } from '../pages/OperatorQueuePage';
import { MarketsPage } from '../pages/MarketsPage';
import { PortfolioPage } from '../pages/PortfolioPage';
import { ProposalsPage } from '../pages/ProposalsPage';
import { PostMortemPage } from '../pages/PostMortemPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SafetyPage } from '../pages/SafetyPage';
import { SemiAutoPage } from '../pages/SemiAutoPage';
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
    label: 'Alerts',
    path: '/alerts',
    description: 'Operator alert center with deduplicated incidents, attention summary, and digest windows.',
    component: AlertsPage,
  },
  {
    label: 'Notifications',
    path: '/notifications',
    description: 'Outbound notification routing for alerts/digests with dedupe, cooldown and delivery audit trail.',
    component: NotificationsPage,
  },
  {
    label: 'Operator Queue',
    path: '/operator-queue',
    description: 'Central exception inbox for approval-required and escalated items that need minimal human intervention.',
    component: OperatorQueuePage,
  },
  {
    label: 'Semi-Auto',
    path: '/semi-auto',
    description: 'Controlled semi-autonomous demo execution with strict policy and paper-only guardrails.',
    component: SemiAutoPage,
  },

  {
    label: 'Real Ops',
    path: '/real-ops',
    description: 'Autonomous scope for real-market read-only data with paper-only execution and strict eligibility controls.',
    component: RealOpsPage,
  },
  {
    label: 'Continuous Demo',
    path: '/continuous-demo',
    description: 'Autonomous continuous demo loop in paper-only mode with strict guardrails, controls, and auditable cycle history.',
    component: ContinuousDemoPage,
  },
  {
    label: 'Automation',
    path: '/automation',
    description: 'Guided demo controls for simulation, signals, portfolio revalue, and review refresh runs.',
    component: AutomationPage,
  },

  {
    label: 'Allocation',
    path: '/allocation',
    description: 'Portfolio-aware capital allocation and execution prioritization for paper/demo proposals.',
    component: AllocationPage,
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
    label: 'Replay',
    path: '/replay',
    description: 'Historical replay/backtest-like simulation over persisted snapshots with isolated paper execution.',
    component: ReplayPage,
  },
  {
    label: 'Evaluation',
    path: '/evaluation',
    description: 'Benchmark and evaluation harness for autonomous paper/demo performance over time.',
    component: EvaluationPage,
  },

  {
    label: 'Experiments',
    path: '/experiments',
    description: 'Strategy profile runner and replay-vs-live paper comparison layer for technical experimentation.',
    component: ExperimentsPage,
  },

  {
    label: 'Readiness',
    path: '/readiness',
    description: 'Go-live readiness and promotion gates audit layer for paper/demo operations.',
    component: ReadinessPage,
  },
  {
    label: 'Runtime',
    path: '/runtime',
    description: 'Operational runtime mode governance for paper/demo autonomy promotion and safety degradations.',
    component: RuntimePage,
  },

  {
    label: 'Learning',
    path: '/learning',
    description: 'Heuristic demo learning memory with auditable adjustments for conservative proposal/risk influence.',
    component: LearningPage,
  },
  {
    label: 'Safety',
    path: '/safety',
    description: 'Operational safety guardrails, cooldowns, kill switch controls, and auditable events for paper/demo mode.',
    component: SafetyPage,
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
