import { AgentsPage } from '../pages/AgentsPage';
import { AutomationPage } from '../pages/AutomationPage';
import { AlertsPage } from '../pages/AlertsPage';
import { CockpitPage } from '../pages/CockpitPage';
import { ChaosPage } from '../pages/ChaosPage';
import { IncidentsPage } from '../pages/IncidentsPage';
import { RunbooksPage } from '../pages/RunbooksPage';
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
import { GoLivePage } from '../pages/GoLivePage';
import { ExecutionVenuePage } from '../pages/ExecutionVenuePage';
import { VenueAccountPage } from '../pages/VenueAccountPage';
import { ConnectorsPage } from '../pages/ConnectorsPage';
import { TracePage } from '../pages/TracePage';
import { AutomationPolicyPage } from '../pages/AutomationPolicyPage';
import { ApprovalsPage } from '../pages/ApprovalsPage';
import { TrustCalibrationPage } from '../pages/TrustCalibrationPage';
import { PolicyTuningPage } from '../pages/PolicyTuningPage';
import { PolicyRolloutPage } from '../pages/PolicyRolloutPage';
import { AutonomyPage } from '../pages/AutonomyPage';
import { AutonomyRolloutPage } from '../pages/AutonomyRolloutPage';
import { AutonomyRoadmapPage } from '../pages/AutonomyRoadmapPage';
import { AutonomyScenariosPage } from '../pages/AutonomyScenariosPage';
import { AutonomyCampaignsPage } from '../pages/AutonomyCampaignsPage';
import { AutonomyProgramPage } from '../pages/AutonomyProgramPage';
import { AutonomySchedulerPage } from '../pages/AutonomySchedulerPage';
import { AutonomyLaunchPage } from '../pages/AutonomyLaunchPage';
import { AutonomyActivationPage } from '../pages/AutonomyActivationPage';
import { AutonomyOperationsPage } from '../pages/AutonomyOperationsPage';
import { AutonomyInterventionsPage } from '../pages/AutonomyInterventionsPage';
import { AutonomyRecoveryPage } from '../pages/AutonomyRecoveryPage';
import { AutonomyDispositionPage } from '../pages/AutonomyDispositionPage';
import { AutonomyCloseoutPage } from '../pages/AutonomyCloseoutPage';
import { AutonomyFollowupPage } from '../pages/AutonomyFollowupPage';
import { AutonomyFeedbackPage } from '../pages/AutonomyFeedbackPage';
import { AutonomyInsightsPage } from '../pages/AutonomyInsightsPage';
import { AutonomyAdvisoryPage } from '../pages/AutonomyAdvisoryPage';
import { AutonomyAdvisoryResolutionPage } from '../pages/AutonomyAdvisoryResolutionPage';
import { AutonomyBacklogPage } from '../pages/AutonomyBacklogPage';
import { AutonomyIntakePage } from '../pages/AutonomyIntakePage';
import { AutonomyPlanningReviewPage } from '../pages/AutonomyPlanningReviewPage';
import { AutonomyDecisionPage } from '../pages/AutonomyDecisionPage';
import { AutonomyPackagePage } from '../pages/AutonomyPackagePage';
import { AutonomyPackageReviewPage } from '../pages/AutonomyPackageReviewPage';
import type { NavRoute } from '../types/system';

export type AppRoute = NavRoute & {
  component: () => JSX.Element;
  match?: (pathname: string) => boolean;
};

export const appRoutes: AppRoute[] = [

  {
    label: 'Cockpit',
    path: '/cockpit',
    description: 'Single-pane operational command center that centralizes posture, incidents, governance, queue pressure, and trace drill-down for manual-first paper/sandbox operations.',
    component: CockpitPage,
  },

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
    label: 'Runbooks',
    path: '/runbooks',
    description: 'Guided manual-first operator remediation workflows with explicit runbook templates, steps, actions, and evidence history.',
    component: RunbooksPage,
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
    label: 'Execution Venue',
    path: '/execution-venue',
    description: 'Canonical external execution contract with sandbox adapter and paper-live parity harness across broker bridge and execution simulator.',
    component: ExecutionVenuePage,
  },


  {
    label: 'Venue Account',
    path: '/venue-account',
    description: 'Sandbox external account mirror and reconciliation layer for external state parity against internal paper portfolio.',
    component: VenueAccountPage,
  },

  {
    label: 'Connectors',
    path: '/connectors',
    description: 'Venue connector certification suite and adapter qualification harness for sandbox-only readiness toward a future read-only phase.',
    component: ConnectorsPage,
  },


  {
    label: 'Autonomy Disposition',
    path: '/autonomy-disposition',
    description: 'Manual-first campaign closure committee for final close/abort/retire decisions with auditable rationale, approvals, and apply controls.',
    component: AutonomyDispositionPage,
  },

  {
    label: 'Autonomy Closeout',
    path: '/autonomy-closeout',
    description: 'Post-disposition campaign archive dossier board with findings, recommendations and explicit memory/postmortem/roadmap handoff governance.',
    component: AutonomyCloseoutPage,
  },

  {
    label: 'Autonomy Followup',
    path: '/autonomy-followup',
    description: 'Manual-first closeout handoff emitter and knowledge routing governance for memory, postmortem, and roadmap/scenario feedback artifacts.',
    component: AutonomyFollowupPage,
  },

  {
    label: 'Autonomy Feedback',
    path: '/autonomy-feedback',
    description: 'Manual-first follow-up resolution tracker that monitors emitted handoffs and closes campaign knowledge loops with auditable status.',
    component: AutonomyFeedbackPage,
  },

  {
    label: 'Autonomy Insights',
    path: '/autonomy-insights',
    description: 'Cross-campaign lessons registry and governance synthesis board derived from closed campaign lifecycle evidence with manual-first recommendations.',
    component: AutonomyInsightsPage,
  },
  {
    label: 'Autonomy Advisory',
    path: '/autonomy-advisory',
    description: 'Insight action emitter and governance note registry that turns reviewed insights into auditable manual-first advisory artifacts.',
    component: AutonomyAdvisoryPage,
  },


  {
    label: 'Autonomy Advisory Resolution',
    path: '/autonomy-advisory-resolution',
    description: 'Manual-first governance note acknowledgment and adoption tracker for emitted advisory artifacts with auditable resolution states.',
    component: AutonomyAdvisoryResolutionPage,
  },

  {
    label: 'Autonomy Backlog',
    path: '/autonomy-backlog',
    description: 'Manual-first governance backlog board that converts adopted/acknowledged advisories into formal future-cycle backlog candidates without auto-apply.',
    component: AutonomyBacklogPage,
  },

  {
    label: 'Autonomy Intake',
    path: '/autonomy-intake',
    description: 'Governed backlog-to-planning proposal intake board that emits auditable roadmap/scenario/program/manager review proposals without auto-apply.',
    component: AutonomyIntakePage,
  },
  {
    label: 'Autonomy Planning Review',
    path: '/autonomy-planning-review',
    description: 'Manual-first planning proposal resolution board that tracks downstream acknowledged/accepted/deferred/rejected outcomes without opaque auto-apply.',
    component: AutonomyPlanningReviewPage,
  },
  {
    label: 'Autonomy Package',
    path: '/autonomy-package',
    description: 'Decision bundle registry that groups registered governance decisions into auditable next-cycle planning seeds with manual-first registration.',
    component: AutonomyPackagePage,
  },
  {
    label: 'Autonomy Package Review',
    path: '/autonomy-package-review',
    description: 'Manual-first governance package resolution board that tracks acknowledged/adopted/deferred/rejected package outcomes without opaque auto-apply.',
    component: AutonomyPackageReviewPage,
  },

  {
    label: 'Autonomy Decision',
    path: '/autonomy-decision',
    description: 'Accepted proposal registry and governance decision package board that formalizes accepted proposals into auditable future-cycle artifacts with manual registration only.',
    component: AutonomyDecisionPage,
  },

  {
    label: 'Autonomy Interventions',
    path: '/autonomy-interventions',
    description: 'Manual remediation gateway for active autonomy campaigns with auditable pause/resume/escalate/review controls.',
    component: AutonomyInterventionsPage,
  },

  {
    label: 'Approvals',
    path: '/approvals',
    description: 'Unified human-in-the-loop approval center centralizing decision gates across runbooks, go-live, and operator queue in paper/sandbox mode.',
    component: ApprovalsPage,
  },

  {
    label: 'Automation Policy',
    path: '/automation-policy',
    description: 'Trust-tiered supervised automation policy matrix for runbooks and operational actions in manual-first paper/sandbox mode.',
    component: AutomationPolicyPage,
  },

  {
    label: 'Trust Calibration',
    path: '/trust-calibration',
    description: 'Approval analytics and human-feedback governance loop that recommends conservative trust-tier tuning in recommendation-only mode.',
    component: TrustCalibrationPage,
  },


  {
    label: 'Policy Tuning',
    path: '/policy-tuning',
    description: 'Manual-first recommendation-to-approval policy tuning board with explicit candidate diff, review decisions, and audited apply flow.',
    component: PolicyTuningPage,
  },
  {
    label: 'Policy Rollout',
    path: '/policy-rollout',
    description: 'Post-change rollout guard for applied policy tuning updates with baseline/post-change comparison, recommendation-first outcomes, and manual rollback loop.',
    component: PolicyRolloutPage,
  },

  {
    label: 'Autonomy',
    path: '/autonomy',
    description: 'Domain-level staged autonomy manager with manual-first recommendations, transitions, and audit-ready apply/rollback flow.',
    component: AutonomyPage,
  },

  {
    label: 'Autonomy Rollout',
    path: '/autonomy-rollout',
    description: 'Post-change domain transition monitor with baseline/post-change comparison, freeze/rollback recommendations, and manual rollback loop.',
    component: AutonomyRolloutPage,
  },

  {
    label: 'Autonomy Roadmap',
    path: '/autonomy-roadmap',
    description: 'Dependency-aware cross-domain autonomy sequencing board with recommendation-first global roadmap plans and manual-first execution gates.',
    component: AutonomyRoadmapPage,
  },

  {
    label: 'Autonomy Scenarios',
    path: '/autonomy-scenarios',
    description: 'Scenario lab for roadmap what-if simulation, bundle/sequence comparison, and recommendation-first autonomy progression decisions.',
    component: AutonomyScenariosPage,
  },


  {
    label: 'Autonomy Program',
    path: '/autonomy-program',
    description: 'Program-level control tower for cross-campaign concurrency guardrails, global health posture, and manual-first recommendations.',
    component: AutonomyProgramPage,
  },
  {
    label: 'Autonomy Scheduler',
    path: '/autonomy-scheduler',
    description: 'Campaign admission board and safe-start window planner for manual-first queue ordering and recommendation-driven campaign admission.',
    component: AutonomySchedulerPage,
  },
  {
    label: 'Autonomy Launch',
    path: '/autonomy-launch',
    description: 'Preflight launch control board for admitted campaigns with explicit readiness checks, blockers, and manual start authorization decisions.',
    component: AutonomyLaunchPage,
  },
  {
    label: 'Autonomy Activation',
    path: '/autonomy-activation',
    description: 'Authorized start handoff gateway that revalidates dispatch constraints and records auditable campaign activation outcomes.',
    component: AutonomyActivationPage,
  },
  {
    label: 'Autonomy Interventions',
    path: '/autonomy-interventions',
    description: 'Manual-first active campaign action board for auditable pause/resume/escalate/abort-review/continue interventions.',
    component: AutonomyInterventionsPage,
  },
  {
    label: 'Autonomy Recovery',
    path: '/autonomy-recovery',
    description: 'Paused campaign resolution board for safe-resume governance with explicit blockers, readiness snapshots, and manual-first close/abort review recommendations.',
    component: AutonomyRecoveryPage,
  },

  {
    label: 'Autonomy Operations',
    path: '/autonomy-operations',
    description: 'Active campaign runtime monitor with explicit progress/stall/blocker signals and manual-first operations recommendations.',
    component: AutonomyOperationsPage,
  },
  {
    label: 'Autonomy Campaigns',
    path: '/autonomy-campaigns',
    description: 'Formal scenario/roadmap handoff into staged, checkpoint-gated autonomy campaign execution programs.',
    component: AutonomyCampaignsPage,
  },

  {
    label: 'Trace Explorer',
    path: '/trace',
    description: 'Unified end-to-end decision provenance and audit graph across orchestrator, memory, execution, venue and incidents.',
    component: TracePage,
  },

  {
    label: 'Go Live Gate',
    path: '/go-live',
    description: 'Final pre-live rehearsal + capital firewall layer with checklist and manual approvals; always dry-run/paper-only in this phase.',
    component: GoLivePage,
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
