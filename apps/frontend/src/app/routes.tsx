import { AgentsPage } from '../pages/AgentsPage';
import { AutomationPage } from '../pages/AutomationPage';
import { AlertsPage } from '../pages/AlertsPage';
import { ChaosPage } from '../pages/ChaosPage';
import { IncidentsPage } from '../pages/IncidentsPage';
import { NotificationsPage } from '../pages/NotificationsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { EvaluationPage } from '../pages/EvaluationPage';
import { ExperimentsPage } from '../pages/ExperimentsPage';
import { ReadinessPage } from '../pages/ReadinessPage';
import { RuntimePage } from '../pages/RuntimePage';
import { ResearchPage } from '../pages/ResearchPage';
import { PredictionPage } from '../pages/PredictionPage';
import { RiskAgentPage } from '../pages/RiskAgentPage';
import { ReplayPage } from '../pages/ReplayPage';
import { LearningPage } from '../pages/LearningPage';
import { MemoryPage } from '../pages/MemoryPage';
import { RealOpsPage } from '../pages/RealOpsPage';
import { ContinuousDemoPage } from '../pages/ContinuousDemoPage';
import { AllocationPage } from '../pages/AllocationPage';
import { MarketDetailPage } from '../pages/MarketDetailPage';
import { OperatorQueuePage } from '../pages/OperatorQueuePage';
import { MarketsPage } from '../pages/MarketsPage';
import { PortfolioPage } from '../pages/PortfolioPage';
import { ExecutionPage } from '../pages/ExecutionPage';
import { PositionsPage } from '../pages/PositionsPage';
import { ProposalsPage } from '../pages/ProposalsPage';
import { PostMortemPage } from '../pages/PostMortemPage';
import { PostmortemBoardPage } from '../pages/PostmortemBoardPage';
import { SettingsPage } from '../pages/SettingsPage';
import { SafetyPage } from '../pages/SafetyPage';
import { SemiAutoPage } from '../pages/SemiAutoPage';
import { SignalsPage } from '../pages/SignalsPage';
import { OpportunitiesPage } from '../pages/OpportunitiesPage';
import { MissionControlPage } from '../pages/MissionControlPage';
import { PortfolioGovernorPage } from '../pages/PortfolioGovernorPage';
import { ProfileManagerPage } from '../pages/ProfileManagerPage';
import { ChampionChallengerPage } from '../pages/ChampionChallengerPage';
import { PromotionPage } from '../pages/PromotionPage';
import { RolloutPage } from '../pages/RolloutPage';
import { SystemPage } from '../pages/SystemPage';
import { CertificationPage } from '../pages/CertificationPage';
import { BrokerBridgePage } from '../pages/BrokerBridgePage';
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
    description: 'Signal fusion opportunity board with composite ranking, proposal gating, and paper/demo-only execution boundaries.',
    component: SignalsPage,
  },
  {
    label: 'Opportunities',
    path: '/opportunities',
    description: 'End-to-end autonomous opportunity supervisor from signal fusion through proposal/allocation and final paper execution path.',
    component: OpportunitiesPage,
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
    label: 'Incidents',
    path: '/incidents',
    description: 'Incident commander center for conservative degraded mode orchestration, mitigation and recovery traceability.',
    component: IncidentsPage,
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
    label: 'Execution',
    path: '/execution',
    description: 'Paper execution realism layer with explicit order lifecycle, attempts, and fills.',
    component: ExecutionPage,
  },

  {
    label: 'Broker Bridge',
    path: '/broker-bridge',
    description: 'Sandbox/dry-run broker routing readiness layer that maps paper execution intents to broker-like payloads under certification/runtime/safety guardrails.',
    component: BrokerBridgePage,
  },
  {
    label: 'Positions',
    path: '/positions',
    description: 'Lifecycle governance for open paper positions with explicit hold/reduce/close/review decisions, queue routing, and paper-only exit plans.',
    component: PositionsPage,
  },
  {
    label: 'Post-Mortem',
    path: '/postmortem',
    description: 'Retrospectives, trade reviews, and learning loops for paper trades.',
    component: PostMortemPage,
    match: (pathname) => /^\/postmortem(\/[^/]+)?\/?$/.test(pathname),
  },
  {
    label: 'Postmortem Board',
    path: '/postmortem-board',
    description: 'Multi-perspective postmortem committee with structured conclusions and learning handoff.',
    component: PostmortemBoardPage,
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
    label: 'Chaos Lab',
    path: '/chaos',
    description: 'Controlled fault injection and resilience benchmark for incident/degraded/rollback validation in paper/demo mode.',
    component: ChaosPage,
  },

  {
    label: 'Experiments',
    path: '/experiments',
    description: 'Strategy profile runner and replay-vs-live paper comparison layer for technical experimentation.',
    component: ExperimentsPage,
  },

  {
    label: 'Certification',
    path: '/certification',
    description: 'Operational certification board that consolidates readiness, resilience, incidents, rollout and execution realism into a paper-only operating envelope.',
    component: CertificationPage,
  },

  {
    label: 'Readiness',
    path: '/readiness',
    description: 'Go-live readiness and promotion gates audit layer for paper/demo operations.',
    component: ReadinessPage,
  },

  {
    label: 'Portfolio Governor',
    path: '/portfolio-governor',
    description: 'Aggregate portfolio exposure governance, concentration checks, and regime-aware throttling for paper/demo entries.',
    component: PortfolioGovernorPage,
  },

  {
    label: 'Champion Challenger',
    path: '/champion-challenger',
    description: 'Shadow benchmark supervisor to compare the active champion stack vs challenger stacks in paper/demo parallel mode.',
    component: ChampionChallengerPage,
  },


  {
    label: 'Promotion Committee',
    path: '/promotion',
    description: 'Controlled evolution pipeline that consolidates execution-aware evidence and emits auditable stack change recommendations.',
    component: PromotionPage,
  },
  {
    label: 'Rollout Manager',
    path: '/rollout',
    description: 'Gradual canary rollout and rollback guardrail operations for paper/demo stack promotion.',
    component: RolloutPage,
  },
  {
    label: 'Profile Manager',
    path: '/profile-manager',
    description: 'Adaptive meta-governance that classifies regime and coordinates operating profiles under runtime/safety/readiness constraints.',
    component: ProfileManagerPage,
  },
  {
    label: 'Mission Control',
    path: '/mission-control',
    description: 'Closed-loop autonomous paper/demo scheduler that orchestrates opportunity cycles, watch, alerts and notifications.',
    component: MissionControlPage,
  },
  {
    label: 'Runtime',
    path: '/runtime',
    description: 'Operational runtime mode governance for paper/demo autonomy promotion and safety degradations.',
    component: RuntimePage,
  },

  {
    label: 'Research',
    path: '/research',
    description: 'RSS-first narrative ingestion and local LLM scan-to-shortlist workflow linked to read-only market probabilities.',
    component: ResearchPage,
  },
  {
    label: 'Risk Agent',
    path: '/risk-agent',
    description: 'Formal risk agent: structured assessment, conservative sizing engine, and open-position watch loop in paper/demo mode.',
    component: RiskAgentPage,
  },
  {
    label: 'Prediction',
    path: '/prediction',
    description: 'Prediction agent MVP with system probability, market implied probability, edge scoring, and confidence output.',
    component: PredictionPage,
  },
  {
    label: 'Learning',
    path: '/learning',
    description: 'Heuristic demo learning memory with auditable adjustments for conservative proposal/risk influence.',
    component: LearningPage,
  },
  {
    label: 'Memory',
    path: '/memory',
    description: 'Semantic precedent retrieval layer for local-first case-based reasoning across research/prediction/risk/postmortem workflows.',
    component: MemoryPage,
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
