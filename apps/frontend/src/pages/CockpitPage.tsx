import { useCallback, useEffect, useMemo, useState } from 'react';

import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import { getCockpitAttention, getCockpitQuickLinks, getCockpitSummary, runCockpitAction } from '../services/cockpit';
import {
  bootstrapLivePaperSession,
  getAutonomousHeartbeatRuns,
  getAutonomousHeartbeatSummary,
  getLivePaperAttentionAlertStatus,
  getLivePaperBootstrapStatus,
  getExtendedPaperRunGate,
  getExtendedPaperRunStatus,
  getLivePaperAutonomyFunnel,
  getLivePaperSmokeTestStatus,
  getLivePaperTrialHistory,
  getLivePaperTrialTrend,
  getLivePaperTrialStatus,
  getLivePaperValidation,
  getTestConsoleExportLog,
  getTestConsoleStatus,
  runLivePaperSmokeTest,
  startExtendedPaperRun,
  startTestConsoleRun,
  stopTestConsoleRun,
  runLivePaperTrial as runLivePaperTrialRequest,
  syncLivePaperAttentionAlert,
} from '../services/missionControl';
import { getPaperAccount, getPaperSnapshots, getPaperSummary } from '../services/paperTrading';
import { getAutonomyScenarioSummary } from '../services/autonomyScenario';
import {
  acknowledgeRuntimeTuningScope,
  clearRuntimeTuningScopeReview,
  getRuntimeTuningCockpitPanel,
  getRuntimeTuningCockpitPanelDetail,
  getRuntimeTuningContextDiffDetail,
  getRuntimeTuningInvestigation,
  getRuntimeTuningReviewAging,
  getRuntimeTuningReviewEscalation,
  getRuntimeTuningReviewActivity,
  getRuntimeTuningReviewQueue,
  getRuntimeTuningAutotriage,
  getRuntimeTuningAutotriageAlertStatus,
  getRuntimeTuningReviewStateDetail,
  getRuntimeTuningScopeTimeline,
  markRuntimeTuningScopeFollowup,
  syncRuntimeTuningAutotriageAlert,
} from '../services/runtime';
import { getScanSummary } from '../services/scanAgent';
import type { CockpitAttentionItem, CockpitQuickActionId, CockpitSnapshot } from '../types/cockpit';
import type {
  AutonomousHeartbeatRun,
  AutonomousHeartbeatSummary,
  LivePaperAttentionAlertStatusResponse,
  LivePaperBootstrapResponse,
  LivePaperBootstrapStatusResponse,
  LivePaperSmokeTestResultResponse,
  LivePaperSmokeTestStatusResponse,
  LivePaperAutonomyFunnelResponse,
  ExtendedPaperRunLaunchResponse,
  ExtendedPaperRunStatusResponse,
  LivePaperFunnelStatus,
  LivePaperTrialRunResultResponse,
  LivePaperTrialHistoryResponse,
  LivePaperExtendedRunGateResponse,
  LivePaperTrialTrendResponse,
  LivePaperTrialRunStatus,
  LivePaperTrialRunStatusResponse,
  LivePaperValidationDigestResponse,
  LlmShadowSummary,
  TestConsoleStatusResponse,
} from '../types/missionControl';
import type {
  RuntimeTuningCockpitPanel,
  RuntimeTuningCockpitPanelDetail,
  RuntimeTuningContextDiff,
  RuntimeTuningInvestigationPacket,
  RuntimeTuningReviewAgingItem,
  RuntimeTuningReviewAging,
  RuntimeTuningReviewQueue,
  RuntimeTuningReviewEscalation,
  RuntimeTuningReviewActivity,
  RuntimeTuningReviewAction,
  RuntimeTuningAutotriageDigest,
  RuntimeTuningAutotriageAlertStatus,
  RuntimeTuningReviewState,
  RuntimeTuningScopeTimeline,
} from '../types/runtime';
import type { PaperAccount, PaperPortfolioSnapshot, PaperPortfolioSummary } from '../types/paperTrading';

const formatDate = (value: string | null | undefined) => (value ? new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'n/a');
const formatDurationSeconds = (value: number | null | undefined) => {
  if (value === null || value === undefined) return 'n/a';
  if (value < 60) return `${value}s`;
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}m ${seconds}s`;
};
const formatRelativeSeconds = (value: string | null | undefined) => {
  if (!value) return 'n/a';
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  return `${seconds}s`;
};
const TEST_CONSOLE_PHASES = ['bootstrap', 'scan', 'consensus_review', 'pursuit_review', 'trial', 'validation', 'trend', 'gate', 'extended_run', 'finalize'];
const parseNumber = (value: string | null | undefined) => {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};
const formatMoney = (value: string | null | undefined, currency = 'USD') => {
  const parsed = parseNumber(value);
  if (parsed === null) return 'n/a';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(parsed);
};
const formatSignedMoney = (value: string | null | undefined, currency = 'USD') => {
  const parsed = parseNumber(value);
  if (parsed === null) return 'n/a';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2, signDisplay: 'always' }).format(parsed);
};
const normalizeTextList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? '').trim()).filter((item) => Boolean(item));
};

const toneFromStatus = (status: string | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = (status ?? '').toUpperCase();
  if (['ACTIVE', 'READY', 'RUNNING', 'SUCCESS', 'PARITY_OK', 'COMPLETED', 'NORMAL', 'ACKNOWLEDGED'].includes(normalized)) return 'ready';
  if (['DEGRADED', 'PAUSED', 'WARNING', 'THROTTLED', 'BLOCK_NEW_ENTRIES', 'PARTIAL', 'CAUTION', 'FOLLOWUP', 'STALE', 'UNREVIEWED'].includes(normalized)) return 'pending';
  if (['FAILED', 'STOPPED', 'ROLLED_BACK', 'REJECTED', 'REMEDIATION_REQUIRED', 'RECERTIFICATION_REQUIRED'].includes(normalized)) return 'offline';
  return 'neutral';
};

const toneFromValidationStatus = (status: LivePaperValidationDigestResponse['validation_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'READY') return 'ready';
  if (status === 'WARNING') return 'pending';
  if (status === 'BLOCKED') return 'offline';
  return 'neutral';
};

const toneFromValidationCheck = (status: 'PASS' | 'WARN' | 'FAIL'): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'PASS') return 'ready';
  if (status === 'WARN') return 'pending';
  if (status === 'FAIL') return 'offline';
  return 'neutral';
};

const toneFromSmokeStatus = (status: 'PASS' | 'WARN' | 'FAIL' | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'PASS') return 'ready';
  if (status === 'WARN') return 'pending';
  if (status === 'FAIL') return 'offline';
  return 'neutral';
};

const toneFromTrialStatus = (status: LivePaperTrialRunStatus | 'IDLE' | 'RUNNING'): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'PASS') return 'ready';
  if (status === 'WARN' || status === 'RUNNING') return 'pending';
  if (status === 'FAIL') return 'offline';
  return 'neutral';
};

const toneFromTrialTrendStatus = (status: LivePaperTrialTrendResponse['trend_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'IMPROVING' || status === 'STABLE') return 'ready';
  if (status === 'INSUFFICIENT_DATA') return 'pending';
  if (status === 'DEGRADING') return 'offline';
  return 'neutral';
};

const toneFromTrialReadinessStatus = (status: LivePaperTrialTrendResponse['readiness_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'READY_FOR_EXTENDED_RUN') return 'ready';
  if (status === 'NEEDS_REVIEW') return 'pending';
  if (status === 'NOT_READY') return 'offline';
  return 'neutral';
};

const toneFromExtendedGateStatus = (status: LivePaperExtendedRunGateResponse['gate_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'ALLOW') return 'ready';
  if (status === 'ALLOW_WITH_CAUTION') return 'pending';
  if (status === 'BLOCK') return 'offline';
  return 'neutral';
};

const toneFromExtendedRunLaunchStatus = (status: ExtendedPaperRunLaunchResponse['launch_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'STARTED' || status === 'REUSED_RUNNING_SESSION' || status === 'REUSED_PAUSED_SESSION') return 'ready';
  if (status === 'BLOCKED') return 'offline';
  if (status === 'FAILED') return 'offline';
  return 'neutral';
};

const toneFromFunnelStatus = (status: LivePaperAutonomyFunnelResponse['funnel_status'] | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'ACTIVE') return 'ready';
  if (status === 'THIN_FLOW') return 'pending';
  if (status === 'STALLED') return 'offline';
  return 'neutral';
};

const toneFromAttentionFunnelStatus = (status: LivePaperFunnelStatus | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  if (status === 'ACTIVE') return 'ready';
  if (status === 'THIN_FLOW') return 'pending';
  if (status === 'STALLED') return 'offline';
  return 'neutral';
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatReasonCode(value: string) {
  return value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

const DEFAULT_TIMELINE_LIMIT = 3;
const REVIEW_STATUS_LABELS: Record<RuntimeTuningReviewState['effective_review_status'], string> = {
  UNREVIEWED: 'UNREVIEWED',
  ACKNOWLEDGED_CURRENT: 'ACKNOWLEDGED',
  FOLLOWUP_REQUIRED: 'FOLLOWUP',
  STALE_REVIEW: 'STALE',
};

const REVIEW_STATUS_HINTS: Record<RuntimeTuningReviewState['effective_review_status'], string> = {
  UNREVIEWED: 'No manual review yet',
  ACKNOWLEDGED_CURRENT: 'Current state acknowledged',
  FOLLOWUP_REQUIRED: 'Follow-up required',
  STALE_REVIEW: 'Review stale',
};

function isAgingQueueItem(item: RuntimeTuningReviewQueue['items'][number] | RuntimeTuningReviewAgingItem): item is RuntimeTuningReviewAgingItem {
  return 'age_bucket' in item && 'age_days' in item && 'aging_rank' in item;
}

function TraceButton({ item }: { item: CockpitAttentionItem }) {
  if (!item.traceRootType || !item.traceRootId) {
    return null;
  }
  return (
    <button
      className="ghost-button"
      type="button"
      onClick={() => navigate(`/trace?root_type=${encodeURIComponent(item.traceRootType ?? '')}&root_id=${encodeURIComponent(item.traceRootId ?? '')}`)}
    >
      Open trace
    </button>
  );
}

export function CockpitPage() {
  const [snapshot, setSnapshot] = useState<CockpitSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [runningAction, setRunningAction] = useState<CockpitQuickActionId | null>(null);
  const [autonomyScenarioSummary, setAutonomyScenarioSummary] = useState<Awaited<ReturnType<typeof getAutonomyScenarioSummary>> | null>(null);
  const [scanSummary, setScanSummary] = useState<Awaited<ReturnType<typeof getScanSummary>> | null>(null);
  const [tuningPanel, setTuningPanel] = useState<RuntimeTuningCockpitPanel | null>(null);
  const [reviewQueue, setReviewQueue] = useState<RuntimeTuningReviewQueue | null>(null);
  const [autotriageDigest, setAutotriageDigest] = useState<RuntimeTuningAutotriageDigest | null>(null);
  const [autotriageAlertStatus, setAutotriageAlertStatus] = useState<RuntimeTuningAutotriageAlertStatus | null>(null);
  const [autotriageAlertSyncMessage, setAutotriageAlertSyncMessage] = useState<string | null>(null);
  const [autotriageAlertSyncError, setAutotriageAlertSyncError] = useState<string | null>(null);
  const [autotriageAlertSyncLoading, setAutotriageAlertSyncLoading] = useState(false);
  const [reviewAging, setReviewAging] = useState<RuntimeTuningReviewAging | null>(null);
  const [reviewEscalation, setReviewEscalation] = useState<RuntimeTuningReviewEscalation | null>(null);
  const [reviewActivity, setReviewActivity] = useState<RuntimeTuningReviewActivity | null>(null);
  const [reviewQueueUnresolvedOnly, setReviewQueueUnresolvedOnly] = useState(true);
  const [reviewQueueStatusFilter, setReviewQueueStatusFilter] = useState<RuntimeTuningReviewState['effective_review_status'] | 'ALL'>('ALL');
  const [reviewQueueAgeBucketFilter, setReviewQueueAgeBucketFilter] = useState<'ALL' | 'FRESH' | 'AGING' | 'OVERDUE'>('ALL');
  const [reviewEscalatedOnly, setReviewEscalatedOnly] = useState(true);
  const [reviewEscalationLevelFilter, setReviewEscalationLevelFilter] = useState<'ALL' | 'MONITOR' | 'ELEVATED' | 'URGENT'>('ALL');
  const [reviewActivityActionTypeFilter, setReviewActivityActionTypeFilter] = useState<RuntimeTuningReviewAction['action_type'] | 'ALL'>('ALL');
  const [reviewActivityLimit, setReviewActivityLimit] = useState<number>(10);
  const [reviewQueueError, setReviewQueueError] = useState<string | null>(null);
  const [attentionOnly, setAttentionOnly] = useState(true);
  const [tuningPanelError, setTuningPanelError] = useState<string | null>(null);
  const [openDiffScope, setOpenDiffScope] = useState<string | null>(null);
  const [openRunContextScope, setOpenRunContextScope] = useState<string | null>(null);
  const [openInvestigationScope, setOpenInvestigationScope] = useState<string | null>(null);
  const [queuedInvestigationScope, setQueuedInvestigationScope] = useState<string | null>(null);
  const [diffCache, setDiffCache] = useState<Record<string, RuntimeTuningContextDiff | null>>({});
  const [panelDetailCache, setPanelDetailCache] = useState<Record<string, RuntimeTuningCockpitPanelDetail | null>>({});
  const [investigationCache, setInvestigationCache] = useState<Record<string, RuntimeTuningInvestigationPacket | null>>({});
  const [timelineCache, setTimelineCache] = useState<Record<string, RuntimeTuningScopeTimeline | null>>({});
  const [timelineErrorCache, setTimelineErrorCache] = useState<Record<string, string | null>>({});
  const [timelineLoadingCache, setTimelineLoadingCache] = useState<Record<string, boolean>>({});
  const [timelineLimitByScope, setTimelineLimitByScope] = useState<Record<string, number>>({});
  const [timelineOnlyNonStableByScope, setTimelineOnlyNonStableByScope] = useState<Record<string, boolean>>({});
  const [reviewStateCache, setReviewStateCache] = useState<Record<string, RuntimeTuningReviewState | null>>({});
  const [reviewStateErrorCache, setReviewStateErrorCache] = useState<Record<string, string | null>>({});
  const [reviewActionLoadingByScope, setReviewActionLoadingByScope] = useState<Record<string, boolean>>({});
  const [reviewActionErrorByScope, setReviewActionErrorByScope] = useState<Record<string, string | null>>({});
  const [livePaperStatus, setLivePaperStatus] = useState<LivePaperBootstrapStatusResponse | null>(null);
  const [livePaperStatusLoading, setLivePaperStatusLoading] = useState(true);
  const [livePaperStatusError, setLivePaperStatusError] = useState<string | null>(null);
  const [livePaperValidation, setLivePaperValidation] = useState<LivePaperValidationDigestResponse | null>(null);
  const [livePaperValidationLoading, setLivePaperValidationLoading] = useState(true);
  const [livePaperValidationError, setLivePaperValidationError] = useState<string | null>(null);
  const [livePaperSmokeStatus, setLivePaperSmokeStatus] = useState<LivePaperSmokeTestStatusResponse | null>(null);
  const [livePaperSmokeStatusLoading, setLivePaperSmokeStatusLoading] = useState(true);
  const [livePaperSmokeStatusError, setLivePaperSmokeStatusError] = useState<string | null>(null);
  const [livePaperSmokeRunLoading, setLivePaperSmokeRunLoading] = useState(false);
  const [livePaperSmokeRunError, setLivePaperSmokeRunError] = useState<string | null>(null);
  const [livePaperSmokeRunResult, setLivePaperSmokeRunResult] = useState<LivePaperSmokeTestResultResponse | null>(null);
  const [livePaperAutonomyFunnel, setLivePaperAutonomyFunnel] = useState<LivePaperAutonomyFunnelResponse | null>(null);
  const [livePaperAutonomyFunnelLoading, setLivePaperAutonomyFunnelLoading] = useState(true);
  const [livePaperAutonomyFunnelError, setLivePaperAutonomyFunnelError] = useState<string | null>(null);
  const [livePaperStartLoading, setLivePaperStartLoading] = useState(false);
  const [livePaperStartError, setLivePaperStartError] = useState<string | null>(null);
  const [livePaperStartResult, setLivePaperStartResult] = useState<LivePaperBootstrapResponse | null>(null);
  const [livePaperOperationalSnapshotLoading, setLivePaperOperationalSnapshotLoading] = useState(true);
  const [livePaperOperationalSnapshotError, setLivePaperOperationalSnapshotError] = useState<string | null>(null);
  const [autonomousHeartbeatSummary, setAutonomousHeartbeatSummary] = useState<AutonomousHeartbeatSummary | null>(null);
  const [latestAutonomousHeartbeatRun, setLatestAutonomousHeartbeatRun] = useState<AutonomousHeartbeatRun | null>(null);
  const [livePaperAttentionStatus, setLivePaperAttentionStatus] = useState<LivePaperAttentionAlertStatusResponse | null>(null);
  const [livePaperAttentionStatusError, setLivePaperAttentionStatusError] = useState<string | null>(null);
  const [livePaperAttentionSyncLoading, setLivePaperAttentionSyncLoading] = useState(false);
  const [livePaperAttentionSyncMessage, setLivePaperAttentionSyncMessage] = useState<string | null>(null);
  const [livePaperAttentionSyncError, setLivePaperAttentionSyncError] = useState<string | null>(null);
  const [paperAccountSnapshot, setPaperAccountSnapshot] = useState<PaperAccount | null>(null);
  const [paperPortfolioSummary, setPaperPortfolioSummary] = useState<PaperPortfolioSummary | null>(null);
  const [paperPortfolioSnapshots, setPaperPortfolioSnapshots] = useState<PaperPortfolioSnapshot[]>([]);
  const [paperPortfolioLoading, setPaperPortfolioLoading] = useState(true);
  const [paperPortfolioError, setPaperPortfolioError] = useState<string | null>(null);
  const [livePaperTrialRequestLoading, setLivePaperTrialRequestLoading] = useState(false);
  const [livePaperTrialStatusLoading, setLivePaperTrialStatusLoading] = useState(true);
  const [livePaperTrialStatus, setLivePaperTrialStatus] = useState<LivePaperTrialRunStatus | 'IDLE' | 'RUNNING'>('IDLE');
  const [livePaperTrialError, setLivePaperTrialError] = useState<string | null>(null);
  const [livePaperTrialNotFound, setLivePaperTrialNotFound] = useState(false);
  const [livePaperTrialResult, setLivePaperTrialResult] = useState<LivePaperTrialRunResultResponse | null>(null);
  const [livePaperTrialStatusSnapshot, setLivePaperTrialStatusSnapshot] = useState<LivePaperTrialRunStatusResponse | null>(null);
  const [livePaperTrialHistoryLoading, setLivePaperTrialHistoryLoading] = useState(true);
  const [livePaperTrialHistoryError, setLivePaperTrialHistoryError] = useState<string | null>(null);
  const [livePaperTrialHistory, setLivePaperTrialHistory] = useState<LivePaperTrialHistoryResponse | null>(null);
  const [livePaperTrialTrendLoading, setLivePaperTrialTrendLoading] = useState(true);
  const [livePaperTrialTrendError, setLivePaperTrialTrendError] = useState<string | null>(null);
  const [livePaperTrialTrend, setLivePaperTrialTrend] = useState<LivePaperTrialTrendResponse | null>(null);
  const [extendedRunGateLoading, setExtendedRunGateLoading] = useState(true);
  const [extendedRunGateError, setExtendedRunGateError] = useState<string | null>(null);
  const [extendedRunGate, setExtendedRunGate] = useState<LivePaperExtendedRunGateResponse | null>(null);
  const [extendedPaperRunStatusLoading, setExtendedPaperRunStatusLoading] = useState(true);
  const [extendedPaperRunStatusError, setExtendedPaperRunStatusError] = useState<string | null>(null);
  const [extendedPaperRunStatus, setExtendedPaperRunStatus] = useState<ExtendedPaperRunStatusResponse | null>(null);
  const [extendedPaperRunStartLoading, setExtendedPaperRunStartLoading] = useState(false);
  const [extendedPaperRunStartError, setExtendedPaperRunStartError] = useState<string | null>(null);
  const [extendedPaperRunLaunch, setExtendedPaperRunLaunch] = useState<ExtendedPaperRunLaunchResponse | null>(null);
  const [testConsoleStatus, setTestConsoleStatus] = useState<TestConsoleStatusResponse | null>(null);
  const [testConsoleStatusLoading, setTestConsoleStatusLoading] = useState(true);
  const [testConsoleStatusError, setTestConsoleStatusError] = useState<string | null>(null);
  const [testConsoleStartLoading, setTestConsoleStartLoading] = useState(false);
  const [testConsoleStopLoading, setTestConsoleStopLoading] = useState(false);
  const [testConsoleExportLoading, setTestConsoleExportLoading] = useState(false);
  const [testConsoleLog, setTestConsoleLog] = useState('No log exported yet');
  const [testConsoleLogError, setTestConsoleLogError] = useState<string | null>(null);
  const [testConsoleCopyMessage, setTestConsoleCopyMessage] = useState<string | null>(null);
  const [testConsoleRawJsonOpen, setTestConsoleRawJsonOpen] = useState(false);
  const heartbeatAutoSyncHint = useMemo(() => {
    const heartbeatSync = autonomousHeartbeatSummary?.live_paper_attention_sync;
    const lastAutoSync = livePaperAttentionStatus?.last_auto_sync;
    const sync = lastAutoSync ?? heartbeatSync;
    if (!sync?.attempted) return 'Attention auto-sync unavailable';
    if (!sync.success || sync.alert_action === 'ERROR') return 'Attention auto-sync active · last result: ERROR';
    return `Attention auto-sync active · Last auto-sync: ${sync.alert_action ?? 'NOOP'}`;
  }, [autonomousHeartbeatSummary, livePaperAttentionStatus]);
  const attentionFunnelUnavailable = livePaperAttentionStatus
    ? !livePaperAttentionStatus.funnel_status
      && !livePaperAttentionStatus.stalled_stage
      && !livePaperAttentionStatus.top_stage
      && !livePaperAttentionStatus.funnel_summary
    : false;
  const paperCurrency = paperAccountSnapshot?.currency ?? paperPortfolioSummary?.account.currency ?? 'USD';
  const openExposure = useMemo(
    () => paperPortfolioSummary?.exposure_by_market.reduce((total, item) => total + (parseNumber(item.market_value) ?? 0), 0) ?? 0,
    [paperPortfolioSummary],
  );
  const latestPaperSnapshot = paperPortfolioSnapshots[0] ?? null;
  const recentPaperTrades = useMemo(() => (paperPortfolioSummary?.recent_trades ?? []).slice(0, 5), [paperPortfolioSummary]);
  const livePaperTrialSnapshot = livePaperTrialResult ?? livePaperTrialStatusSnapshot;
  const livePaperTrialChecks = livePaperTrialResult?.checks ?? [];
  const livePaperTrialHistoryItems = livePaperTrialHistory?.items ?? [];
  const livePaperTrialRecentStatuses = livePaperTrialTrend?.recent_statuses ?? [];
  const extendedRunGateChecks = extendedRunGate?.checks ?? [];
  const extendedPaperRunReasonCodes = extendedPaperRunLaunch?.reason_codes ?? extendedRunGate?.reason_codes ?? [];
  const extendedPaperRunPrimaryLabel = extendedPaperRunLaunch?.launch_status ?? extendedPaperRunStatus?.gate_status ?? extendedRunGate?.gate_status ?? 'UNKNOWN';
  const extendedPaperRunPrimaryTone = extendedPaperRunLaunch?.launch_status
    ? toneFromExtendedRunLaunchStatus(extendedPaperRunLaunch.launch_status)
    : toneFromExtendedGateStatus(extendedPaperRunStatus?.gate_status ?? extendedRunGate?.gate_status);
  const extendedPaperRunSummary = extendedPaperRunLaunch?.launch_summary ?? extendedPaperRunStatus?.status_summary ?? 'No extended run launch yet.';
  const extendedPaperRunHint = extendedPaperRunLaunch?.next_action_hint ?? extendedPaperRunStatus?.next_action_hint ?? 'Refresh status to get latest hint.';
  const testConsoleScanSummary = typeof testConsoleStatus?.scan_summary === 'string'
    ? testConsoleStatus.scan_summary
    : testConsoleStatus?.scan_summary?.summary ?? 'n/a';
  const testConsolePortfolioSummary = typeof testConsoleStatus?.portfolio_summary === 'string'
    ? testConsoleStatus.portfolio_summary
    : testConsoleStatus?.portfolio_summary?.summary ?? 'n/a';
  const testConsoleRunActive = Boolean(
    testConsoleStatus?.test_status
      && ['RUNNING', 'IN_PROGRESS', 'ACTIVE'].includes(testConsoleStatus.test_status.toUpperCase()),
  );
  const testConsoleCurrentStep = testConsoleStatus?.current_step ?? (testConsoleStatus?.current_phase ? TEST_CONSOLE_PHASES.indexOf(testConsoleStatus.current_phase) + 1 : null);
  const testConsoleTotalSteps = testConsoleStatus?.total_steps ?? TEST_CONSOLE_PHASES.length;
  const testConsoleProgressPercent = testConsoleCurrentStep && testConsoleTotalSteps
    ? Math.min(100, Math.max(0, Math.round((testConsoleCurrentStep / testConsoleTotalSteps) * 100)))
    : 0;
  const testConsoleCurrentStepLabel = testConsoleStatus?.current_step_label ?? testConsoleStatus?.current_phase ?? 'Sin etapa';
  const testConsoleUpdatedAgo = formatRelativeSeconds(testConsoleStatus?.updated_at);
  const testConsoleHasExportableLog = Boolean(
    testConsoleLog
      && testConsoleLog !== 'No log exported yet'
      && testConsoleLog !== 'Unable to export test log',
  );
  const testConsoleCanExportLog = Boolean(testConsoleStatus && !testConsoleStatusError);
  const llmShadowSummary = testConsoleStatus?.llm_shadow_summary ?? null;
  const latestLlmShadowSummary = (testConsoleStatus?.latest_llm_shadow_summary ?? llmShadowSummary) as LlmShadowSummary | null;
  const llmShadowHistory = useMemo(
    () => (testConsoleStatus?.llm_shadow_recent_history ?? []).slice(0, 3),
    [testConsoleStatus?.llm_shadow_recent_history],
  );
  const llmShadowKeyRisks = normalizeTextList(latestLlmShadowSummary?.key_risks);
  const llmShadowSupportingPoints = normalizeTextList(latestLlmShadowSummary?.key_supporting_points);
  const llmAuxSignalSummary = testConsoleStatus?.llm_aux_signal_summary ?? null;
  const llmAuxReasonCodes = normalizeTextList(llmAuxSignalSummary?.aux_signal_reason_codes);
  const llmShadowHistoryCount = testConsoleStatus?.llm_shadow_history_count ?? llmShadowHistory.length;

  const loadLivePaperStatus = useCallback(async (): Promise<LivePaperBootstrapStatusResponse | null> => {
    setLivePaperStatusLoading(true);
    setLivePaperStatusError(null);
    try {
      const payload = await getLivePaperBootstrapStatus();
      setLivePaperStatus(payload);
      return payload;
    } catch (statusError) {
      setLivePaperStatus(null);
      setLivePaperStatusError(getErrorMessage(statusError, 'Could not load live paper autopilot status.'));
      return null;
    } finally {
      setLivePaperStatusLoading(false);
    }
  }, []);

  const loadTestConsoleStatus = useCallback(async (): Promise<TestConsoleStatusResponse | null> => {
    setTestConsoleStatusLoading(true);
    setTestConsoleStatusError(null);
    try {
      const payload = await getTestConsoleStatus();
      setTestConsoleStatus(payload);
      return payload;
    } catch {
      setTestConsoleStatus(null);
      setTestConsoleStatusError('Test Console unavailable');
      return null;
    } finally {
      setTestConsoleStatusLoading(false);
    }
  }, []);

  const exportTestConsoleLog = useCallback(async () => {
    setTestConsoleExportLoading(true);
    setTestConsoleLogError(null);
    try {
      const payload = await getTestConsoleExportLog('text');
      const textPayload = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
      setTestConsoleLog(textPayload || 'No log exported yet');
    } catch {
      setTestConsoleLog('Unable to export test log');
      setTestConsoleLogError('Unable to export test log');
    } finally {
      setTestConsoleExportLoading(false);
    }
  }, []);

  const startTestConsoleFromCockpit = useCallback(async () => {
    setTestConsoleStartLoading(true);
    setTestConsoleStatusError(null);
    setTestConsoleCopyMessage(null);
    try {
      const payload = await startTestConsoleRun();
      setTestConsoleStatus(payload);
      await loadTestConsoleStatus();
      await exportTestConsoleLog();
    } catch {
      setTestConsoleStatusError('Test Console unavailable');
    } finally {
      setTestConsoleStartLoading(false);
    }
  }, [exportTestConsoleLog, loadTestConsoleStatus]);

  const stopTestConsoleFromCockpit = useCallback(async () => {
    setTestConsoleStopLoading(true);
    setTestConsoleStatusError(null);
    try {
      const payload = await stopTestConsoleRun();
      setTestConsoleStatus(payload);
      await loadTestConsoleStatus();
    } catch {
      setTestConsoleStatusError('Test Console unavailable');
    } finally {
      setTestConsoleStopLoading(false);
    }
  }, [loadTestConsoleStatus]);

  const copyTestConsoleLog = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(testConsoleLog || 'No log exported yet');
      setTestConsoleCopyMessage('Log copied');
    } catch {
      setTestConsoleCopyMessage('Unable to copy log');
    }
  }, [testConsoleLog]);

  const loadLivePaperValidation = useCallback(async (): Promise<LivePaperValidationDigestResponse | null> => {
    setLivePaperValidationLoading(true);
    setLivePaperValidationError(null);
    try {
      const payload = await getLivePaperValidation();
      setLivePaperValidation(payload);
      return payload;
    } catch (validationError) {
      setLivePaperValidation(null);
      setLivePaperValidationError(getErrorMessage(validationError, 'Live paper validation unavailable'));
      return null;
    } finally {
      setLivePaperValidationLoading(false);
    }
  }, []);

  const loadLivePaperSmokeTestStatus = useCallback(async (): Promise<LivePaperSmokeTestStatusResponse | null> => {
    setLivePaperSmokeStatusLoading(true);
    setLivePaperSmokeStatusError(null);
    try {
      const payload = await getLivePaperSmokeTestStatus();
      setLivePaperSmokeStatus(payload);
      return payload;
    } catch (smokeStatusError) {
      setLivePaperSmokeStatus(null);
      const message = getErrorMessage(smokeStatusError, 'Live paper smoke test unavailable');
      if (message.toLowerCase().includes('no smoke test has been executed yet')) {
        setLivePaperSmokeStatusError('No smoke test result yet');
      } else {
        setLivePaperSmokeStatusError('Live paper smoke test unavailable');
      }
      return null;
    } finally {
      setLivePaperSmokeStatusLoading(false);
    }
  }, []);

  const loadLivePaperAutonomyFunnel = useCallback(async () => {
    setLivePaperAutonomyFunnelLoading(true);
    setLivePaperAutonomyFunnelError(null);
    try {
      const payload = await getLivePaperAutonomyFunnel({ window_minutes: 60, preset: 'live_read_only_paper_conservative' });
      setLivePaperAutonomyFunnel(payload);
    } catch (funnelError) {
      setLivePaperAutonomyFunnel(null);
      setLivePaperAutonomyFunnelError(getErrorMessage(funnelError, 'Autonomy funnel unavailable'));
    } finally {
      setLivePaperAutonomyFunnelLoading(false);
    }
  }, []);

  const loadLivePaperOperationalSnapshot = useCallback(async () => {
    setLivePaperOperationalSnapshotLoading(true);
    setLivePaperOperationalSnapshotError(null);
    setLivePaperAttentionStatusError(null);
    try {
      const [heartbeatSummaryResult, heartbeatRunsResult, attentionStatusResult] = await Promise.allSettled([
        getAutonomousHeartbeatSummary(),
        getAutonomousHeartbeatRuns(),
        getLivePaperAttentionAlertStatus(),
      ]);

      if (heartbeatSummaryResult.status === 'fulfilled') {
        setAutonomousHeartbeatSummary(heartbeatSummaryResult.value);
      } else {
        setAutonomousHeartbeatSummary(null);
      }

      if (heartbeatRunsResult.status === 'fulfilled') {
        setLatestAutonomousHeartbeatRun(heartbeatRunsResult.value[0] ?? null);
      } else {
        setLatestAutonomousHeartbeatRun(null);
      }

      if (attentionStatusResult.status === 'fulfilled') {
        setLivePaperAttentionStatus(attentionStatusResult.value);
      } else {
        setLivePaperAttentionStatus(null);
        setLivePaperAttentionStatusError('Attention auto-sync unavailable');
      }

      if (heartbeatSummaryResult.status === 'rejected' || heartbeatRunsResult.status === 'rejected') {
        setLivePaperOperationalSnapshotError('Operational snapshot unavailable.');
      }
    } catch (snapshotError) {
      setAutonomousHeartbeatSummary(null);
      setLatestAutonomousHeartbeatRun(null);
      setLivePaperAttentionStatus(null);
      setLivePaperOperationalSnapshotError(getErrorMessage(snapshotError, 'Operational snapshot unavailable.'));
      setLivePaperAttentionStatusError('Attention auto-sync unavailable');
    } finally {
      setLivePaperOperationalSnapshotLoading(false);
    }
  }, []);

  const loadPaperPortfolioSnapshot = useCallback(async () => {
    setPaperPortfolioLoading(true);
    setPaperPortfolioError(null);
    try {
      const [accountResult, summaryResult, snapshotsResult] = await Promise.allSettled([
        getPaperAccount(),
        getPaperSummary(),
        getPaperSnapshots(),
      ]);

      if (accountResult.status === 'fulfilled') setPaperAccountSnapshot(accountResult.value);
      else setPaperAccountSnapshot(null);

      if (summaryResult.status === 'fulfilled') setPaperPortfolioSummary(summaryResult.value);
      else setPaperPortfolioSummary(null);

      if (snapshotsResult.status === 'fulfilled') setPaperPortfolioSnapshots(snapshotsResult.value);
      else setPaperPortfolioSnapshots([]);

      if (accountResult.status === 'rejected' && summaryResult.status === 'rejected' && snapshotsResult.status === 'rejected') {
        setPaperPortfolioError('Paper portfolio snapshot unavailable');
      }
    } catch (portfolioError) {
      setPaperAccountSnapshot(null);
      setPaperPortfolioSummary(null);
      setPaperPortfolioSnapshots([]);
      setPaperPortfolioError(getErrorMessage(portfolioError, 'Paper portfolio snapshot unavailable'));
    } finally {
      setPaperPortfolioLoading(false);
    }
  }, []);

  const startLivePaperAutopilot = useCallback(async () => {
    setLivePaperStartLoading(true);
    setLivePaperStartError(null);
    setLivePaperStartResult(null);
    try {
      const payload = await bootstrapLivePaperSession();
      setLivePaperStartResult(payload);
      await Promise.all([loadLivePaperStatus(), loadLivePaperOperationalSnapshot(), loadPaperPortfolioSnapshot(), loadLivePaperValidation(), loadLivePaperAutonomyFunnel()]);
    } catch (startError) {
      setLivePaperStartError(getErrorMessage(startError, 'Could not start live paper autopilot.'));
    } finally {
      setLivePaperStartLoading(false);
    }
  }, [loadLivePaperOperationalSnapshot, loadLivePaperStatus, loadPaperPortfolioSnapshot, loadLivePaperValidation, loadLivePaperAutonomyFunnel]);

  const runLivePaperSmokeTestFromCockpit = useCallback(async () => {
    setLivePaperSmokeRunLoading(true);
    setLivePaperSmokeRunError(null);
    setLivePaperSmokeRunResult(null);
    try {
      const payload = await runLivePaperSmokeTest({
        preset: 'live_read_only_paper_conservative',
        heartbeat_passes: 1,
      });
      setLivePaperSmokeRunResult(payload);
      setLivePaperSmokeStatus({
        preset_name: payload.preset_name,
        smoke_test_status: payload.smoke_test_status,
        executed_at: payload.executed_at,
        validation_status_after: payload.validation_status_after,
        heartbeat_passes_completed: payload.heartbeat_passes_completed,
        smoke_test_summary: payload.smoke_test_summary,
        next_action_hint: payload.next_action_hint,
      });
      await Promise.all([loadLivePaperSmokeTestStatus(), loadLivePaperValidation(), loadLivePaperAutonomyFunnel()]);
    } catch (smokeRunError) {
      setLivePaperSmokeRunError(getErrorMessage(smokeRunError, 'Live paper smoke test unavailable'));
    } finally {
      setLivePaperSmokeRunLoading(false);
    }
  }, [loadLivePaperSmokeTestStatus, loadLivePaperValidation, loadLivePaperAutonomyFunnel]);

  const loadLivePaperTrialStatus = useCallback(async () => {
    setLivePaperTrialStatusLoading(true);
    setLivePaperTrialError(null);
    try {
      const payload = await getLivePaperTrialStatus();
      setLivePaperTrialStatusSnapshot(payload);
      setLivePaperTrialStatus(payload.trial_status);
      setLivePaperTrialNotFound(false);
      return payload;
    } catch (statusError) {
      const message = getErrorMessage(statusError, 'Could not load live paper trial status.');
      if (message.toLowerCase().includes('no live paper trial run has been executed yet')) {
        setLivePaperTrialNotFound(true);
        setLivePaperTrialStatus('IDLE');
        setLivePaperTrialStatusSnapshot(null);
        setLivePaperTrialError(null);
      } else {
        setLivePaperTrialError(message);
      }
      return null;
    } finally {
      setLivePaperTrialStatusLoading(false);
    }
  }, []);

  const loadLivePaperTrialHistory = useCallback(async () => {
    setLivePaperTrialHistoryLoading(true);
    setLivePaperTrialHistoryError(null);
    try {
      const payload = await getLivePaperTrialHistory({ limit: 5 });
      setLivePaperTrialHistory(payload);
      return payload;
    } catch (historyError) {
      setLivePaperTrialHistory(null);
      setLivePaperTrialHistoryError(getErrorMessage(historyError, 'Could not load live paper trial history.'));
      return null;
    } finally {
      setLivePaperTrialHistoryLoading(false);
    }
  }, []);

  const loadLivePaperTrialTrend = useCallback(async () => {
    setLivePaperTrialTrendLoading(true);
    setLivePaperTrialTrendError(null);
    try {
      const payload = await getLivePaperTrialTrend({ limit: 5, preset: 'live_read_only_paper_conservative' });
      setLivePaperTrialTrend(payload);
      return payload;
    } catch {
      setLivePaperTrialTrend(null);
      setLivePaperTrialTrendError('Trial trend unavailable');
      return null;
    } finally {
      setLivePaperTrialTrendLoading(false);
    }
  }, []);

  const loadExtendedRunGate = useCallback(async () => {
    setExtendedRunGateLoading(true);
    setExtendedRunGateError(null);
    try {
      const payload = await getExtendedPaperRunGate({ preset: 'live_read_only_paper_conservative' });
      setExtendedRunGate(payload);
      return payload;
    } catch {
      setExtendedRunGate(null);
      setExtendedRunGateError('Extended run gate unavailable');
      return null;
    } finally {
      setExtendedRunGateLoading(false);
    }
  }, []);

  const loadExtendedPaperRunStatus = useCallback(async () => {
    setExtendedPaperRunStatusLoading(true);
    setExtendedPaperRunStatusError(null);
    try {
      const payload = await getExtendedPaperRunStatus({ preset: 'live_read_only_paper_conservative' });
      setExtendedPaperRunStatus(payload);
      return payload;
    } catch (statusError) {
      setExtendedPaperRunStatus(null);
      setExtendedPaperRunStatusError(getErrorMessage(statusError, 'Extended paper run status unavailable.'));
      return null;
    } finally {
      setExtendedPaperRunStatusLoading(false);
    }
  }, []);

  const startExtendedPaperRunFromCockpit = useCallback(async () => {
    setExtendedPaperRunStartLoading(true);
    setExtendedPaperRunStartError(null);
    try {
      const payload = await startExtendedPaperRun({ preset: 'live_read_only_paper_conservative' });
      setExtendedPaperRunLaunch(payload);
      await Promise.all([
        loadExtendedPaperRunStatus(),
        loadExtendedRunGate(),
        loadLivePaperStatus(),
        loadLivePaperOperationalSnapshot(),
      ]);
    } catch (startError) {
      setExtendedPaperRunStartError(getErrorMessage(startError, 'Extended paper run launch failed.'));
    } finally {
      setExtendedPaperRunStartLoading(false);
    }
  }, [loadExtendedPaperRunStatus, loadExtendedRunGate, loadLivePaperOperationalSnapshot, loadLivePaperStatus]);

  const runLivePaperTrial = useCallback(async () => {
    setLivePaperTrialRequestLoading(true);
    setLivePaperTrialStatus('RUNNING');
    setLivePaperTrialError(null);
    try {
      const payload = await runLivePaperTrialRequest({
        preset: 'live_read_only_paper_conservative',
        heartbeat_passes: 1,
      });
      setLivePaperTrialResult(payload);
      setLivePaperTrialStatus(payload.trial_status);
      setLivePaperTrialNotFound(false);
      await Promise.all([loadLivePaperTrialStatus(), loadLivePaperTrialHistory(), loadLivePaperTrialTrend(), loadExtendedRunGate()]);
      await Promise.all([
        loadLivePaperStatus(),
        loadLivePaperValidation(),
        loadLivePaperSmokeTestStatus(),
        loadLivePaperOperationalSnapshot(),
        loadPaperPortfolioSnapshot(),
        loadLivePaperAutonomyFunnel(),
      ]);
    } catch (trialError) {
      setLivePaperTrialStatus('FAIL');
      setLivePaperTrialError(getErrorMessage(trialError, 'Live paper trial run failed.'));
    } finally {
      setLivePaperTrialRequestLoading(false);
    }
  }, [loadExtendedRunGate, loadLivePaperAutonomyFunnel, loadLivePaperOperationalSnapshot, loadLivePaperSmokeTestStatus, loadLivePaperStatus, loadLivePaperTrialHistory, loadLivePaperTrialStatus, loadLivePaperTrialTrend, loadLivePaperValidation, loadPaperPortfolioSnapshot]);

  const refreshLivePaperTrialStatus = useCallback(async () => {
    setLivePaperTrialStatus('RUNNING');
    await loadLivePaperTrialStatus();
  }, [loadLivePaperTrialStatus]);

  const refreshLivePaperTrialTrend = useCallback(async () => {
    await Promise.all([loadLivePaperTrialTrend(), loadExtendedRunGate()]);
  }, [loadExtendedRunGate, loadLivePaperTrialTrend]);

  const refreshLivePaperValidation = useCallback(async () => {
    await Promise.all([loadLivePaperValidation(), loadExtendedRunGate()]);
  }, [loadExtendedRunGate, loadLivePaperValidation]);

  const loadCockpit = useCallback(async () => {
    setLoading(true);
    setError(null);
    setTuningPanelError(null);
    setReviewQueueError(null);
    try {
      const [response, scenarioSummary, scanSummaryResponse, tuningPanelResponse, reviewQueueResponse, reviewAgingResponse, reviewEscalationResponse, reviewActivityResponse, autotriageResponse, autotriageAlertStatusResponse] = await Promise.all([
        getCockpitSummary(),
        getAutonomyScenarioSummary(),
        getScanSummary(),
        getRuntimeTuningCockpitPanel({ attention_only: attentionOnly, limit: 5 }),
        getRuntimeTuningReviewQueue({
          unresolved_only: reviewQueueUnresolvedOnly,
          effective_review_status: reviewQueueStatusFilter === 'ALL' ? undefined : reviewQueueStatusFilter,
          limit: 8,
        }),
        getRuntimeTuningReviewAging({
          unresolved_only: reviewQueueUnresolvedOnly,
          age_bucket: reviewQueueAgeBucketFilter === 'ALL' ? undefined : reviewQueueAgeBucketFilter,
          limit: 8,
        }),
        getRuntimeTuningReviewEscalation({
          escalated_only: reviewEscalatedOnly,
          escalation_level: reviewEscalationLevelFilter === 'ALL' ? undefined : reviewEscalationLevelFilter,
          limit: 6,
        }),
        getRuntimeTuningReviewActivity({
          action_type: reviewActivityActionTypeFilter === 'ALL' ? undefined : reviewActivityActionTypeFilter,
          limit: reviewActivityLimit,
        }),
        getRuntimeTuningAutotriage({ top_n: 3, include_monitor: false }),
        getRuntimeTuningAutotriageAlertStatus(),
      ]);
      setSnapshot(response);
      setAutonomyScenarioSummary(scenarioSummary);
      setScanSummary(scanSummaryResponse);
      setTuningPanel(tuningPanelResponse);
      setReviewQueue(reviewQueueResponse);
      setReviewAging(reviewAgingResponse);
      setReviewEscalation(reviewEscalationResponse);
      setReviewActivity(reviewActivityResponse);
      setAutotriageDigest(autotriageResponse);
      setAutotriageAlertStatus(autotriageAlertStatusResponse);
      setReviewStateCache({});
      setReviewStateErrorCache({});
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load cockpit data.'));
      setSnapshot(null);
      setTuningPanelError(getErrorMessage(loadError, 'Could not load runtime tuning attention panel.'));
      setReviewQueueError(getErrorMessage(loadError, 'Could not load runtime tuning review queue.'));
      setAutotriageDigest(null);
      setAutotriageAlertStatus(null);
    } finally {
      setLoading(false);
    }
  }, [
    attentionOnly,
    reviewActivityActionTypeFilter,
    reviewActivityLimit,
    reviewEscalatedOnly,
    reviewEscalationLevelFilter,
    reviewQueueAgeBucketFilter,
    reviewQueueStatusFilter,
    reviewQueueUnresolvedOnly,
  ]);

  useEffect(() => {
    void loadCockpit();
  }, [loadCockpit]);

  useEffect(() => {
    void loadLivePaperStatus();
  }, [loadLivePaperStatus]);

  useEffect(() => {
    void loadTestConsoleStatus();
  }, [loadTestConsoleStatus]);

  useEffect(() => {
    if (!testConsoleRunActive && !testConsoleStartLoading) return undefined;
    const timer = window.setInterval(() => {
      void loadTestConsoleStatus();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [loadTestConsoleStatus, testConsoleRunActive, testConsoleStartLoading]);

  useEffect(() => {
    void loadLivePaperOperationalSnapshot();
  }, [loadLivePaperOperationalSnapshot]);

  useEffect(() => {
    void loadLivePaperValidation();
  }, [loadLivePaperValidation]);

  useEffect(() => {
    void loadLivePaperSmokeTestStatus();
  }, [loadLivePaperSmokeTestStatus]);

  useEffect(() => {
    void loadLivePaperTrialStatus();
  }, [loadLivePaperTrialStatus]);

  useEffect(() => {
    void loadLivePaperTrialHistory();
  }, [loadLivePaperTrialHistory]);

  useEffect(() => {
    void loadLivePaperTrialTrend();
  }, [loadLivePaperTrialTrend]);

  useEffect(() => {
    void loadExtendedRunGate();
  }, [loadExtendedRunGate]);

  useEffect(() => {
    void loadExtendedPaperRunStatus();
  }, [loadExtendedPaperRunStatus]);

  useEffect(() => {
    void loadLivePaperAutonomyFunnel();
  }, [loadLivePaperAutonomyFunnel]);

  useEffect(() => {
    void loadPaperPortfolioSnapshot();
  }, [loadPaperPortfolioSnapshot]);

  useEffect(() => {
    if (!tuningPanel?.items?.length) return;
    const missingScopes = tuningPanel.items
      .map((item) => item.source_scope)
      .filter((scope) => reviewStateCache[scope] === undefined && reviewStateErrorCache[scope] === undefined);
    if (missingScopes.length === 0) return;
    void Promise.all(
      missingScopes.map(async (scope) => {
        try {
          const reviewState = await getRuntimeTuningReviewStateDetail(scope);
          setReviewStateCache((current) => ({ ...current, [scope]: reviewState }));
          setReviewStateErrorCache((current) => ({ ...current, [scope]: null }));
        } catch (reviewError) {
          setReviewStateCache((current) => ({ ...current, [scope]: null }));
          setReviewStateErrorCache((current) => ({
            ...current,
            [scope]: getErrorMessage(reviewError, 'Could not load manual review state.'),
          }));
        }
      }),
    );
  }, [reviewStateCache, reviewStateErrorCache, tuningPanel]);

  const attention = useMemo(() => (snapshot ? getCockpitAttention(snapshot) : []), [snapshot]);
  const quickLinks = useMemo(() => getCockpitQuickLinks(), []);

  const runAction = useCallback(
    async (action: CockpitQuickActionId) => {
      if (!snapshot) return;
      setRunningAction(action);
      setActionError(null);
      setActionMessage(null);
      try {
        const runId = snapshot.rollout?.current_run?.id;
        await runCockpitAction(action, runId ? { runId } : undefined);
        setActionMessage(`Action ${action} executed.`);
        await loadCockpit();
      } catch (err) {
        setActionError(getErrorMessage(err, `Action ${action} failed.`));
      } finally {
        setRunningAction(null);
      }
    },
    [loadCockpit, snapshot],
  );

  const viewDiff = useCallback(
    async (sourceScope: string, snapshotId: number | null) => {
      setOpenDiffScope((current) => (current === sourceScope ? null : sourceScope));
      if (!snapshotId || diffCache[sourceScope]) return;
      try {
        const diff = await getRuntimeTuningContextDiffDetail(snapshotId);
        setDiffCache((current) => ({ ...current, [sourceScope]: diff }));
      } catch {
        setDiffCache((current) => ({ ...current, [sourceScope]: null }));
      }
    },
    [diffCache],
  );

  const viewRunContext = useCallback(
    async (sourceScope: string) => {
      setOpenRunContextScope((current) => (current === sourceScope ? null : sourceScope));
      if (panelDetailCache[sourceScope]) return;
      try {
        const detail = await getRuntimeTuningCockpitPanelDetail(sourceScope);
        setPanelDetailCache((current) => ({ ...current, [sourceScope]: detail }));
      } catch {
        setPanelDetailCache((current) => ({ ...current, [sourceScope]: null }));
      }
    },
    [panelDetailCache],
  );

  const loadScopeTimeline = useCallback(
    async (sourceScope: string, overrides?: { limit?: number; onlyNonStable?: boolean }) => {
      const limit = overrides?.limit ?? timelineLimitByScope[sourceScope] ?? DEFAULT_TIMELINE_LIMIT;
      const onlyNonStable = overrides?.onlyNonStable ?? timelineOnlyNonStableByScope[sourceScope] ?? false;

      setTimelineLimitByScope((current) => ({ ...current, [sourceScope]: limit }));
      setTimelineOnlyNonStableByScope((current) => ({ ...current, [sourceScope]: onlyNonStable }));
      setTimelineLoadingCache((current) => ({ ...current, [sourceScope]: true }));
      setTimelineErrorCache((current) => ({ ...current, [sourceScope]: null }));
      try {
        const timeline = await getRuntimeTuningScopeTimeline(sourceScope, {
          limit,
          include_stable: !onlyNonStable,
        });
        setTimelineCache((current) => ({ ...current, [sourceScope]: timeline }));
      } catch (timelineError) {
        setTimelineCache((current) => ({ ...current, [sourceScope]: null }));
        setTimelineErrorCache((current) => ({
          ...current,
          [sourceScope]: getErrorMessage(timelineError, 'Could not load recent timeline.'),
        }));
      } finally {
        setTimelineLoadingCache((current) => ({ ...current, [sourceScope]: false }));
      }
    },
    [timelineLimitByScope, timelineOnlyNonStableByScope],
  );

  const investigateScope = useCallback(async (sourceScope: string) => {
    setOpenInvestigationScope(sourceScope);
    if (!investigationCache[sourceScope]) {
      try {
        const packet = await getRuntimeTuningInvestigation(sourceScope);
        setInvestigationCache((current) => ({ ...current, [sourceScope]: packet }));
      } catch {
        setInvestigationCache((current) => ({ ...current, [sourceScope]: null }));
      }
    }

    if (!timelineCache[sourceScope] && !timelineLoadingCache[sourceScope]) {
      void loadScopeTimeline(sourceScope, { limit: DEFAULT_TIMELINE_LIMIT, onlyNonStable: false });
    }
  }, [investigationCache, loadScopeTimeline, timelineCache, timelineLoadingCache]);

  const runManualReviewAction = useCallback(
    async (sourceScope: string, action: 'ACKNOWLEDGE' | 'FOLLOWUP' | 'CLEAR') => {
      setReviewActionLoadingByScope((current) => ({ ...current, [sourceScope]: true }));
      setReviewActionErrorByScope((current) => ({ ...current, [sourceScope]: null }));
      try {
        if (action === 'ACKNOWLEDGE') {
          await acknowledgeRuntimeTuningScope(sourceScope);
        } else if (action === 'FOLLOWUP') {
          await markRuntimeTuningScopeFollowup(sourceScope);
        } else {
          await clearRuntimeTuningScopeReview(sourceScope);
        }
        const refreshedReviewState = await getRuntimeTuningReviewStateDetail(sourceScope);
        setReviewStateCache((current) => ({ ...current, [sourceScope]: refreshedReviewState }));
        setReviewStateErrorCache((current) => ({ ...current, [sourceScope]: null }));
      } catch (reviewActionError) {
        setReviewActionErrorByScope((current) => ({
          ...current,
          [sourceScope]: getErrorMessage(reviewActionError, 'Manual review action failed.'),
        }));
      } finally {
        setReviewActionLoadingByScope((current) => ({ ...current, [sourceScope]: false }));
      }
    },
    [],
  );

  const syncAutotriageAttentionAlert = useCallback(async () => {
    setAutotriageAlertSyncLoading(true);
    setAutotriageAlertSyncMessage(null);
    setAutotriageAlertSyncError(null);
    try {
      const payload = await syncRuntimeTuningAutotriageAlert();
      const refreshedStatus = await getRuntimeTuningAutotriageAlertStatus();
      setAutotriageAlertStatus(refreshedStatus);
      const suppressionHint = payload.update_suppressed && payload.suppression_reason ? ` (${payload.suppression_reason})` : '';
      setAutotriageAlertSyncMessage(`Attention alert sync: ${payload.alert_action}${suppressionHint}.`);
    } catch (syncError) {
      setAutotriageAlertSyncError(getErrorMessage(syncError, 'Could not sync runtime tuning attention alert.'));
    } finally {
      setAutotriageAlertSyncLoading(false);
    }
  }, []);

  const syncLivePaperAttentionAlertManual = useCallback(async () => {
    setLivePaperAttentionSyncLoading(true);
    setLivePaperAttentionSyncMessage(null);
    setLivePaperAttentionSyncError(null);
    try {
      const payload = await syncLivePaperAttentionAlert();
      await loadLivePaperOperationalSnapshot();
      setLivePaperAttentionSyncMessage(`Sync attention alert: ${payload.alert_action}.`);
    } catch (syncError) {
      setLivePaperAttentionSyncError(getErrorMessage(syncError, 'Could not sync live paper operational attention alert.'));
    } finally {
      setLivePaperAttentionSyncLoading(false);
    }
  }, [loadLivePaperOperationalSnapshot]);

  useEffect(() => {
    if (!queuedInvestigationScope || !tuningPanel?.items?.length) return;
    if (!tuningPanel.items.some((item) => item.source_scope === queuedInvestigationScope)) return;
    void investigateScope(queuedInvestigationScope);
    setQueuedInvestigationScope(null);
  }, [investigateScope, queuedInvestigationScope, tuningPanel]);

  return (
    <div className="page-stack cockpit-page">
      <PageHeader
        eyebrow="Advanced / Cockpit"
        title="Cockpit"
        actions={<div className="button-row"><button className="secondary-button" type="button" onClick={() => void loadCockpit()}>Actualizar cockpit</button><button className="ghost-button" type="button" onClick={() => navigate('/mission-control')}>Abrir Mission Control</button></div>}
      />

      <SectionCard eyebrow="Acciones rápidas" title="Controles manuales principales" description="Atajos de operación frecuentes. Las opciones más técnicas están en módulos específicos.">
        <div className="button-row">
          <button className="primary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_START')}>Iniciar misión</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_PAUSE')}>Pausar misión</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('MISSION_CONTROL_RESUME')}>Reanudar misión</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('INCIDENT_DETECTION')}>Detectar incidentes</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('CERTIFICATION_REVIEW')}>Revisar certificación</button>
          <button className="secondary-button" type="button" disabled={runningAction !== null} onClick={() => void runAction('PORTFOLIO_GOVERNANCE')}>Revisar gobernanza de portfolio</button>
        </div>
        {actionMessage ? <p className="success-text">{actionMessage}</p> : null}
        {actionError ? <p className="error-text">{actionError}</p> : null}
      </SectionCard>

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!snapshot ? null : (
          <>
            <SectionCard eyebrow="System posture" title="Runtime, degraded mode, certification and profile" description="Fast answer to whether the stack is healthy or constrained.">
              <div className="cockpit-metric-grid">
                <div><strong>Runtime mode:</strong> <StatusBadge tone={toneFromStatus(snapshot.runtime?.state.current_mode)}>{snapshot.runtime?.state.current_mode ?? 'n/a'}</StatusBadge></div>
                <div><strong>Runtime status:</strong> <StatusBadge tone={toneFromStatus(snapshot.runtime?.state.status)}>{snapshot.runtime?.state.status ?? 'n/a'}</StatusBadge></div>
                <div><strong>Degraded mode:</strong> <StatusBadge tone={toneFromStatus(snapshot.incidents?.degraded_mode.state)}>{snapshot.incidents?.degraded_mode.state ?? 'n/a'}</StatusBadge></div>
                <div><strong>Certification:</strong> <StatusBadge tone={toneFromStatus(snapshot.certification?.latest_run?.certification_level)}>{snapshot.certification?.latest_run?.certification_level ?? 'NOT_CERTIFIED'}</StatusBadge></div>
                <div><strong>Profile regime:</strong> <StatusBadge tone={toneFromStatus(snapshot.profile?.current_regime)}>{snapshot.profile?.current_regime ?? 'n/a'}</StatusBadge></div>
                <div><strong>Profile recommendation:</strong> {snapshot.profile?.target_profiles.mission_control ?? 'n/a'}</div>
              </div>
            </SectionCard>

            <div className="content-grid content-grid--two-columns">
              <SectionCard
                eyebrow="Mission control bootstrap"
                title="Live Paper Autopilot"
                description="Real market data in read-only mode with paper-only execution. This does not enable live trading."
              >
                {livePaperStatusLoading ? (
                  <p>Loading live paper autopilot status…</p>
                ) : null}
                {livePaperStatusError ? <p className="error-text">{livePaperStatusError}</p> : null}
                {livePaperStatus ? (
                  <ul className="key-value-list">
                    <li><span>Preset</span><strong>{livePaperStatus.preset_name}</strong></li>
                    <li><span>Session</span><strong><StatusBadge tone={livePaperStatus.session_active ? 'ready' : 'pending'}>{livePaperStatus.session_active ? 'ACTIVE' : 'INACTIVE'}</StatusBadge></strong></li>
                    <li><span>Heartbeat</span><strong><StatusBadge tone={livePaperStatus.heartbeat_active ? 'ready' : 'pending'}>{livePaperStatus.heartbeat_active ? 'ACTIVE' : 'INACTIVE'}</StatusBadge></strong></li>
                    <li><span>Runtime mode</span><strong>{livePaperStatus.runtime_mode}</strong></li>
                    <li><span>Market data</span><strong>{livePaperStatus.market_data_mode}</strong></li>
                    <li><span>Paper execution</span><strong>{livePaperStatus.paper_execution_mode}</strong></li>
                    <li><span>Session status</span><strong>{livePaperStatus.current_session_status}</strong></li>
                    <li><span>Status summary</span><strong>{livePaperStatus.status_summary}</strong></li>
                    <li><span>Operator hint</span><strong>{livePaperStatus.operator_attention_hint}</strong></li>
                  </ul>
                ) : null}
                <div className="button-row">
                  <StatusBadge tone="ready">REAL_READ_ONLY</StatusBadge>
                  <StatusBadge tone="ready">PAPER_ONLY</StatusBadge>
                  <StatusBadge tone="ready">live_execution_enabled = false</StatusBadge>
                </div>
                <SectionCard
                  eyebrow="Single-pane V1 operator flow"
                  title="Test Console"
                  description="Compact supervised runner for V1 paper validation: start, stop, refresh status, export/copy logs. This does not enable live trading."
                >
                  <div className="button-row">
                    <StatusBadge tone={toneFromStatus(testConsoleStatus?.test_status)}>{testConsoleStatus?.test_status ?? 'UNKNOWN'}</StatusBadge>
                    <StatusBadge tone={toneFromStatus(testConsoleStatus?.progress_state)}>{testConsoleStatus?.progress_state ?? 'idle'}</StatusBadge>
                    <StatusBadge tone={toneFromStatus(testConsoleStatus?.validation_status)}>{testConsoleStatus?.validation_status ?? 'n/a'}</StatusBadge>
                    <StatusBadge tone={toneFromStatus(testConsoleStatus?.trial_status)}>{testConsoleStatus?.trial_status ?? 'n/a'}</StatusBadge>
                    <StatusBadge tone={toneFromStatus(testConsoleStatus?.gate_status)}>{testConsoleStatus?.gate_status ?? 'n/a'}</StatusBadge>
                    {testConsoleStatus?.is_stale ? <StatusBadge tone="pending">STALE</StatusBadge> : null}
                    {testConsoleStatus?.export_available ? <StatusBadge tone="ready">EXPORT AVAILABLE</StatusBadge> : null}
                  </div>
                  {testConsoleStatusLoading ? <p>Loading Test Console status…</p> : null}
                  {!testConsoleStatusLoading && testConsoleStatusError ? <p className="warning-text">{testConsoleStatusError}</p> : null}
                  {testConsoleStatus ? (
                    <>
                      <div className="test-console-progress">
                        <div className="test-console-progress__bar" role="progressbar" aria-valuenow={testConsoleProgressPercent} aria-valuemin={0} aria-valuemax={100}>
                          <div className="test-console-progress__fill" style={{ width: `${testConsoleProgressPercent}%` }} />
                        </div>
                        <p className="muted-text">Etapa actual: {testConsoleCurrentStepLabel} · Paso {testConsoleCurrentStep ?? 0} de {testConsoleTotalSteps} · Última actualización hace {testConsoleUpdatedAgo}</p>
                      </div>
                      <ul className="key-value-list">
                      <li><span>Current phase</span><strong>{testConsoleStatus.current_phase ?? 'n/a'}</strong></li>
                      <li><span>Started at</span><strong>{formatDate(testConsoleStatus.started_at)}</strong></li>
                      <li><span>Updated at</span><strong>{formatDate(testConsoleStatus.updated_at)}</strong></li>
                      <li><span>Ended at</span><strong>{formatDate(testConsoleStatus.ended_at)}</strong></li>
                      <li><span>Elapsed time</span><strong>{formatDurationSeconds(testConsoleStatus.elapsed_seconds)}</strong></li>
                      <li><span>Validation status</span><strong>{testConsoleStatus.validation_status ?? 'n/a'}</strong></li>
                      <li><span>Trial status</span><strong>{testConsoleStatus.trial_status ?? 'n/a'}</strong></li>
                      <li><span>Trend status</span><strong>{testConsoleStatus.trend_status ?? 'n/a'}</strong></li>
                      <li><span>Readiness status</span><strong>{testConsoleStatus.readiness_status ?? 'n/a'}</strong></li>
                      <li><span>Gate status</span><strong>{testConsoleStatus.gate_status ?? 'n/a'}</strong></li>
                      <li><span>Extended run status</span><strong>{testConsoleStatus.extended_run_status ?? 'n/a'}</strong></li>
                      <li><span>Attention mode</span><strong>{testConsoleStatus.attention_mode ?? 'n/a'}</strong></li>
                      <li><span>Funnel status</span><strong>{testConsoleStatus.funnel_status ?? 'n/a'}</strong></li>
                      <li><span>Scan summary</span><strong>{testConsoleScanSummary}</strong></li>
                      <li><span>Portfolio summary</span><strong>{testConsolePortfolioSummary}</strong></li>
                      <li><span>Last event</span><strong>{testConsoleStatus.last_event ?? 'n/a'}</strong></li>
                      <li><span>Last reason code</span><strong>{testConsoleStatus.last_reason_code ?? 'n/a'}</strong></li>
                      <li><span>Next action hint</span><strong>{testConsoleStatus.next_action_hint ?? 'n/a'}</strong></li>
                      {testConsoleStatus.blocker_summary ? (
                        <li><span>Blocker summary</span><strong>{testConsoleStatus.blocker_summary}</strong></li>
                      ) : null}
                      </ul>
                    </>
                  ) : null}
                  <div className="button-row test-console-actions">
                    <button className="secondary-button" type="button" disabled={testConsoleStartLoading || testConsoleStopLoading} onClick={() => void startTestConsoleFromCockpit()}>
                      {testConsoleStartLoading ? 'Starting…' : 'Start test'}
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      title={testConsoleRunActive ? 'Stop active test' : 'Not available: no active test'}
                      disabled={testConsoleStopLoading || testConsoleStartLoading || !testConsoleRunActive}
                      onClick={() => void stopTestConsoleFromCockpit()}
                    >
                      {testConsoleStopLoading ? 'Stopping…' : testConsoleRunActive ? 'Stop test' : 'Stop test · Not available'}
                    </button>
                    <button className="ghost-button" type="button" disabled={testConsoleStatusLoading} onClick={() => void loadTestConsoleStatus()}>
                      Refresh status
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      title={testConsoleCanExportLog ? 'Export current test log' : 'Not available: no test status yet'}
                      disabled={testConsoleExportLoading || !testConsoleCanExportLog}
                      onClick={() => void exportTestConsoleLog()}
                    >
                      {testConsoleExportLoading ? 'Exporting…' : 'Export log'}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      title={testConsoleHasExportableLog ? 'Copy exported log' : 'Not available: export log first'}
                      disabled={testConsoleExportLoading || !testConsoleHasExportableLog}
                      onClick={() => void copyTestConsoleLog()}
                    >
                      {testConsoleHasExportableLog ? 'Copy log' : 'Copy log · No data yet'}
                    </button>
                    <button className="ghost-button" type="button" onClick={() => setTestConsoleRawJsonOpen((value) => !value)}>
                      {testConsoleRawJsonOpen ? 'Hide raw JSON' : 'View raw JSON'}
                    </button>
                  </div>
                  {testConsoleCopyMessage ? <p className="muted-text">{testConsoleCopyMessage}</p> : null}
                  {testConsoleLogError ? <p className="warning-text">{testConsoleLogError}</p> : null}
                  <SectionCard
                    eyebrow="Advanced analysis layer"
                    title="LLM Shadow + Aux Signal (advisory-only)"
                    description="Auxiliary analysis only. This panel does not decide execution, remains paper-only, and is intentionally separated from core action controls."
                  >
                    <div className="button-row">
                      <StatusBadge tone="pending">ADVANCED</StatusBadge>
                      <StatusBadge tone={latestLlmShadowSummary?.advisory_only === false ? 'offline' : 'ready'}>advisory_only={String(latestLlmShadowSummary?.advisory_only ?? true)}</StatusBadge>
                      <StatusBadge tone={Boolean(latestLlmShadowSummary?.affects_execution) ? 'offline' : 'ready'}>affects_execution={String(Boolean(latestLlmShadowSummary?.affects_execution))}</StatusBadge>
                      <StatusBadge tone={latestLlmShadowSummary?.paper_only === false ? 'offline' : 'ready'}>paper_only={String(latestLlmShadowSummary?.paper_only ?? true)}</StatusBadge>
                      <StatusBadge tone="neutral">analysis_auxiliary_layer</StatusBadge>
                    </div>
                    <ul className="key-value-list">
                      <li><span>Provider / model</span><strong>{latestLlmShadowSummary?.provider ?? 'n/a'} / {latestLlmShadowSummary?.model ?? 'n/a'}</strong></li>
                      <li><span>Shadow reasoning status</span><strong><StatusBadge tone={toneFromStatus(latestLlmShadowSummary?.llm_shadow_reasoning_status)}>{latestLlmShadowSummary?.llm_shadow_reasoning_status ?? 'UNAVAILABLE'}</StatusBadge></strong></li>
                      <li><span>Stance</span><strong>{latestLlmShadowSummary?.stance ?? 'unclear'}</strong></li>
                      <li><span>Confidence</span><strong>{latestLlmShadowSummary?.confidence ?? 'low'}</strong></li>
                      <li><span>Recommendation mode</span><strong>{latestLlmShadowSummary?.recommendation_mode ?? 'observe'}</strong></li>
                      <li><span>Summary</span><strong>{latestLlmShadowSummary?.summary ?? 'No LLM shadow summary available yet.'}</strong></li>
                      <li><span>Aux signal status</span><strong><StatusBadge tone={toneFromStatus(llmAuxSignalSummary?.aux_signal_status)}>{llmAuxSignalSummary?.aux_signal_status ?? 'DISABLED'}</StatusBadge></strong></li>
                      <li><span>Aux recommendation</span><strong>{llmAuxSignalSummary?.aux_signal_recommendation ?? 'observe'}</strong></li>
                      <li><span>Aux signal weight</span><strong>{llmAuxSignalSummary?.aux_signal_weight ?? 0}</strong></li>
                      <li><span>Aux summary</span><strong>{llmAuxSignalSummary?.summary ?? 'No aux signal summary.'}</strong></li>
                    </ul>
                    <div className="content-grid content-grid--two-columns">
                      <div className="subsection">
                        <p className="section-label">Key risks</p>
                        {llmShadowKeyRisks.length > 0 ? <ul>{llmShadowKeyRisks.map((risk, index) => <li key={`${risk}-${index}`}>{risk}</li>)}</ul> : <p className="muted-text">No key risks reported.</p>}
                      </div>
                      <div className="subsection">
                        <p className="section-label">Supporting points</p>
                        {llmShadowSupportingPoints.length > 0 ? <ul>{llmShadowSupportingPoints.map((point, index) => <li key={`${point}-${index}`}>{point}</li>)}</ul> : <p className="muted-text">No supporting points reported.</p>}
                      </div>
                    </div>
                    <div className="subsection">
                      <p className="section-label">Aux signal reason codes</p>
                      {llmAuxReasonCodes.length > 0 ? <ul>{llmAuxReasonCodes.map((reasonCode, index) => <li key={`${reasonCode}-${index}`}>{reasonCode}</li>)}</ul> : <p className="muted-text">No aux reason codes.</p>}
                    </div>
                    <div className="subsection">
                      <p className="section-label">Recent shadow artifacts (last {llmShadowHistory.length})</p>
                      <p className="muted-text">Total persisted history: {llmShadowHistoryCount}.</p>
                      {llmShadowHistory.length > 0 ? (
                        <ul className="key-value-list">
                          {llmShadowHistory.map((item, index) => (
                            <li key={`llm-shadow-history-${item.artifact_id ?? index}`}>
                              <span>
                                {formatDate(item.timestamp)} · stance={item.stance ?? 'unclear'} · confidence={item.confidence ?? 'low'}
                              </span>
                              <strong>{item.recommendation_mode ?? 'observe'} · {item.llm_shadow_reasoning_status ?? 'UNAVAILABLE'}</strong>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted-text">No recent shadow artifacts yet.</p>
                      )}
                    </div>
                  </SectionCard>
                  <div className="subsection test-console-output-block">
                    <p className="section-label">Exported log</p>
                    <pre className="test-console-output">{testConsoleLog || 'No log exported yet'}</pre>
                  </div>
                  {testConsoleRawJsonOpen ? (
                    <div className="subsection test-console-output-block">
                      <p className="section-label">Raw status JSON</p>
                      <pre className="test-console-output">{JSON.stringify(testConsoleStatus ?? {}, null, 2)}</pre>
                    </div>
                  ) : null}
                </SectionCard>
                <SectionCard
                  eyebrow="Economic snapshot"
                  title="Paper Portfolio Snapshot"
                  description="Compact fake-money snapshot for validating that live-read-only paper autopilot is moving."
                >
                  {paperPortfolioLoading ? <p>Loading paper portfolio snapshot…</p> : null}
                  {!paperPortfolioLoading && paperPortfolioError ? <p className="warning-text">{paperPortfolioError}</p> : null}
                  {!paperPortfolioLoading && !paperPortfolioError ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone="ready">fake_money_only</StatusBadge>
                        <StatusBadge tone={Number(paperAccountSnapshot?.open_positions_count ?? paperPortfolioSummary?.open_positions_count ?? 0) > 0 ? 'pending' : 'neutral'}>
                          Open positions {paperAccountSnapshot?.open_positions_count ?? paperPortfolioSummary?.open_positions_count ?? 0}
                        </StatusBadge>
                        <StatusBadge tone={(parseNumber(paperAccountSnapshot?.total_pnl) ?? 0) >= 0 ? 'ready' : 'offline'}>
                          Total PnL {formatSignedMoney(paperAccountSnapshot?.total_pnl, paperCurrency)}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Cash balance</span><strong>{formatMoney(paperAccountSnapshot?.cash_balance, paperCurrency)}</strong></li>
                        <li><span>Total equity</span><strong>{formatMoney(paperAccountSnapshot?.equity, paperCurrency)}</strong></li>
                        <li><span>Realized PnL</span><strong>{formatSignedMoney(paperAccountSnapshot?.realized_pnl, paperCurrency)}</strong></li>
                        <li><span>Unrealized PnL</span><strong>{formatSignedMoney(paperAccountSnapshot?.unrealized_pnl, paperCurrency)}</strong></li>
                        <li><span>Open positions count</span><strong>{paperAccountSnapshot?.open_positions_count ?? paperPortfolioSummary?.open_positions_count ?? 0}</strong></li>
                        <li><span>Total positions exposure</span><strong>{formatMoney(String(openExposure), paperCurrency)}</strong></li>
                        <li><span>Recent paper trades</span><strong>{paperPortfolioSummary?.recent_trades.length ?? 0}</strong></li>
                        <li><span>Latest snapshot</span><strong>{formatDate(latestPaperSnapshot?.captured_at ?? paperAccountSnapshot?.updated_at)}</strong></li>
                      </ul>
                      {recentPaperTrades.length > 0 ? (
                        <div className="subsection">
                          <p className="section-label">Recent paper trades</p>
                          <ul className="key-value-list">
                            {recentPaperTrades.map((trade) => (
                              <li key={trade.id}>
                                <span>{trade.market__title}</span>
                                <strong>{trade.trade_type} {trade.side} · qty {trade.quantity} · px {trade.price} · {formatDate(trade.executed_at)}</strong>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <p className="muted-text">No recent paper trades yet.</p>
                      )}
                    </>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={paperPortfolioLoading}
                      onClick={() => {
                        void Promise.all([loadPaperPortfolioSnapshot(), loadLivePaperValidation()]);
                      }}
                    >
                      Refresh portfolio
                    </button>
                    <button className="ghost-button" type="button" onClick={() => navigate('/portfolio')}>Open portfolio</button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="One-click V1 trial"
                  title="Live Paper Trial Run"
                  description="Backend-driven compact trial run (bootstrap + smoke + validation) for REAL_READ_ONLY + PAPER_ONLY safety."
                >
                  <div className="button-row">
                    <StatusBadge tone={toneFromTrialStatus(livePaperTrialStatus)}>
                      {livePaperTrialStatus}
                    </StatusBadge>
                    <StatusBadge tone="ready">REAL_READ_ONLY</StatusBadge>
                    <StatusBadge tone="ready">PAPER_ONLY</StatusBadge>
                  </div>
                  {livePaperTrialStatusLoading ? <p>Loading live paper trial status…</p> : null}
                  {!livePaperTrialStatusLoading && livePaperTrialNotFound ? <p className="muted-text">No trial run yet.</p> : null}
                  {!livePaperTrialStatusLoading && !livePaperTrialNotFound ? (
                    <ul className="key-value-list">
                      <li><span>Trial summary</span><strong>{livePaperTrialSnapshot?.trial_summary ?? 'n/a'}</strong></li>
                      <li><span>Next action hint</span><strong>{livePaperTrialSnapshot?.next_action_hint ?? 'n/a'}</strong></li>
                      <li><span>Bootstrap action</span><strong>{livePaperTrialResult?.bootstrap_action ?? 'n/a'}</strong></li>
                      <li><span>Smoke test status</span><strong>{livePaperTrialSnapshot?.smoke_test_status ?? 'n/a'}</strong></li>
                      <li><span>Validation status before</span><strong>{livePaperTrialResult?.validation_status_before ?? 'n/a'}</strong></li>
                      <li><span>Validation status after</span><strong>{livePaperTrialResult?.validation_status_after ?? livePaperTrialStatusSnapshot?.validation_status_after ?? 'n/a'}</strong></li>
                      <li><span>Heartbeat passes completed</span><strong>{livePaperTrialSnapshot?.heartbeat_passes_completed ?? 'n/a'}</strong></li>
                      <li><span>Recent activity detected</span><strong>{livePaperTrialResult ? String(livePaperTrialResult.recent_activity_detected) : 'n/a'}</strong></li>
                      <li><span>Recent trades detected</span><strong>{livePaperTrialResult ? String(livePaperTrialResult.recent_trades_detected) : 'n/a'}</strong></li>
                      <li><span>Portfolio snapshot ready</span><strong>{livePaperTrialResult ? String(livePaperTrialResult.portfolio_snapshot_ready) : 'n/a'}</strong></li>
                    </ul>
                  ) : null}
                  {!livePaperTrialStatusLoading && !livePaperTrialNotFound && livePaperTrialChecks.length > 0 ? (
                    <div className="subsection">
                      <p className="section-label">Trial checks</p>
                      <ul className="key-value-list">
                        {livePaperTrialChecks.map((check) => (
                          <li key={check.check_name}>
                            <span>{check.check_name}</span>
                            <strong>{check.status} · {check.summary}</strong>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {livePaperTrialError ? <p className="warning-text">{livePaperTrialError}</p> : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={livePaperTrialRequestLoading}
                      onClick={() => void runLivePaperTrial()}
                    >
                      {livePaperTrialRequestLoading ? 'Running…' : 'Run trial'}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={livePaperTrialStatusLoading || livePaperTrialRequestLoading}
                      onClick={() => void refreshLivePaperTrialStatus()}
                    >
                      Refresh trial status
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Compact readiness signal"
                  title="Trial Trend"
                  description="Operational digest of recent trial history to quickly assess trend and readiness for an extended paper run."
                >
                  {livePaperTrialTrendLoading ? <p>Loading trial trend…</p> : null}
                  {!livePaperTrialTrendLoading && livePaperTrialTrendError ? <p className="warning-text">{livePaperTrialTrendError}</p> : null}
                  {!livePaperTrialTrendLoading && !livePaperTrialTrendError && livePaperTrialTrend ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromTrialTrendStatus(livePaperTrialTrend.trend_status)}>
                          {livePaperTrialTrend.trend_status}
                        </StatusBadge>
                        <StatusBadge tone={toneFromTrialReadinessStatus(livePaperTrialTrend.readiness_status)}>
                          {livePaperTrialTrend.readiness_status}
                        </StatusBadge>
                        <StatusBadge tone="neutral">{livePaperTrialTrend.sample_size} runs</StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Trend summary</span><strong>{livePaperTrialTrend.trend_summary}</strong></li>
                        <li><span>Next action hint</span><strong>{livePaperTrialTrend.next_action_hint}</strong></li>
                        <li><span>Latest trial status</span><strong>{livePaperTrialTrend.latest_trial_status ?? 'n/a'}</strong></li>
                        <li><span>Latest validation status</span><strong>{livePaperTrialTrend.latest_validation_status ?? 'n/a'}</strong></li>
                        <li><span>PASS / WARN / FAIL</span><strong>{livePaperTrialTrend.counts.pass_count} / {livePaperTrialTrend.counts.warn_count} / {livePaperTrialTrend.counts.fail_count}</strong></li>
                        {livePaperTrialRecentStatuses.length > 0 ? (
                          <li><span>Recent statuses</span><strong>{livePaperTrialRecentStatuses.join(' → ')}</strong></li>
                        ) : null}
                      </ul>
                    </>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={livePaperTrialTrendLoading || livePaperTrialRequestLoading}
                      onClick={() => void refreshLivePaperTrialTrend()}
                    >
                      Refresh trend
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Go / caution / hold"
                  title="Extended Run Gate"
                  description="Compact decision layer to determine if V1 paper is ready for a longer paper trial."
                >
                  {extendedRunGateLoading ? <p>Loading extended run gate…</p> : null}
                  {!extendedRunGateLoading && extendedRunGateError ? <p className="warning-text">Extended run gate unavailable.</p> : null}
                  {!extendedRunGateLoading && !extendedRunGateError && extendedRunGate ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromExtendedGateStatus(extendedRunGate.gate_status)}>{extendedRunGate.gate_status}</StatusBadge>
                        <StatusBadge tone={toneFromTrialStatus(extendedRunGate.latest_trial_status ?? 'IDLE')}>
                          Trial {extendedRunGate.latest_trial_status ?? 'n/a'}
                        </StatusBadge>
                        <StatusBadge tone={toneFromTrialTrendStatus(extendedRunGate.trend_status)}>
                          Trend {extendedRunGate.trend_status ?? 'n/a'}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Gate summary</span><strong>{extendedRunGate.gate_summary}</strong></li>
                        <li><span>Next action hint</span><strong>{extendedRunGate.next_action_hint}</strong></li>
                        <li><span>Readiness status</span><strong>{extendedRunGate.readiness_status ?? 'n/a'}</strong></li>
                        <li><span>Validation status</span><strong>{extendedRunGate.validation_status ?? 'n/a'}</strong></li>
                        <li><span>Attention mode</span><strong>{extendedRunGate.attention_mode ?? 'n/a'}</strong></li>
                        <li><span>Funnel status</span><strong>{extendedRunGate.funnel_status ?? 'n/a'}</strong></li>
                      </ul>
                      {extendedRunGate.reason_codes && extendedRunGate.reason_codes.length > 0 ? (
                        <div className="subsection">
                          <p className="section-label">Reason codes</p>
                          <div className="button-row">
                            {extendedRunGate.reason_codes.slice(0, 6).map((code) => (
                              <StatusBadge key={code} tone="neutral">{formatReasonCode(code)}</StatusBadge>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {extendedRunGateChecks.length > 0 ? (
                        <div className="subsection">
                          <p className="section-label">Checks</p>
                          <ul className="key-value-list">
                            {extendedRunGateChecks.map((check) => (
                              <li key={check.check_name}>
                                <span>{check.check_name}</span>
                                <strong>{check.status} · {check.summary}</strong>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={extendedRunGateLoading || livePaperTrialRequestLoading}
                      onClick={() => void loadExtendedRunGate()}
                    >
                      Refresh gate
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Operational launcher"
                  title="Extended Paper Run"
                  description="Start or reuse a longer paper-only run after gate checks. Keeps REAL_READ_ONLY + PAPER_ONLY constraints."
                >
                  <div className="button-row">
                    <StatusBadge tone={extendedPaperRunPrimaryTone}>{extendedPaperRunPrimaryLabel}</StatusBadge>
                    <StatusBadge tone={toneFromExtendedGateStatus(extendedPaperRunStatus?.gate_status ?? extendedRunGate?.gate_status)}>
                      Gate {(extendedPaperRunStatus?.gate_status ?? extendedRunGate?.gate_status) ?? 'n/a'}
                    </StatusBadge>
                    <StatusBadge tone={(extendedPaperRunStatus?.extended_run_active ?? false) ? 'ready' : 'neutral'}>
                      Extended run {(extendedPaperRunStatus?.extended_run_active ?? false) ? 'ACTIVE' : 'INACTIVE'}
                    </StatusBadge>
                  </div>
                  {extendedPaperRunStatusLoading ? <p>Loading extended paper run status…</p> : null}
                  {!extendedPaperRunStatusLoading && extendedPaperRunStatusError ? <p className="warning-text">{extendedPaperRunStatusError}</p> : null}
                  <ul className="key-value-list">
                    <li><span>Launch summary</span><strong>{extendedPaperRunSummary}</strong></li>
                    <li><span>Next action hint</span><strong>{extendedPaperRunHint}</strong></li>
                    <li><span>Launch status</span><strong>{extendedPaperRunLaunch?.launch_status ?? 'n/a'}</strong></li>
                    <li><span>Gate status</span><strong>{extendedPaperRunStatus?.gate_status ?? extendedRunGate?.gate_status ?? 'n/a'}</strong></li>
                    <li><span>Session active</span><strong>{String(extendedPaperRunStatus?.session_active ?? extendedPaperRunLaunch?.session_active ?? false)}</strong></li>
                    <li><span>Heartbeat active</span><strong>{String(extendedPaperRunStatus?.heartbeat_active ?? extendedPaperRunLaunch?.heartbeat_active ?? false)}</strong></li>
                    <li><span>Current session status</span><strong>{extendedPaperRunStatus?.current_session_status ?? extendedPaperRunLaunch?.current_session_status ?? 'n/a'}</strong></li>
                    <li><span>Caution mode</span><strong>{String(extendedPaperRunStatus?.caution_mode ?? extendedPaperRunLaunch?.caution_mode ?? false)}</strong></li>
                    <li><span>Extended run active</span><strong>{String(extendedPaperRunStatus?.extended_run_active ?? false)}</strong></li>
                  </ul>
                  <div className="button-row">
                    <StatusBadge tone={(extendedPaperRunStatus?.session_active ?? extendedPaperRunLaunch?.session_active ?? false) ? 'ready' : 'neutral'}>
                      Session {(extendedPaperRunStatus?.session_active ?? extendedPaperRunLaunch?.session_active ?? false) ? 'active' : 'inactive'}
                    </StatusBadge>
                    <StatusBadge tone={(extendedPaperRunStatus?.heartbeat_active ?? extendedPaperRunLaunch?.heartbeat_active ?? false) ? 'ready' : 'neutral'}>
                      Heartbeat {(extendedPaperRunStatus?.heartbeat_active ?? extendedPaperRunLaunch?.heartbeat_active ?? false) ? 'active' : 'inactive'}
                    </StatusBadge>
                    <StatusBadge tone={(extendedPaperRunStatus?.caution_mode ?? extendedPaperRunLaunch?.caution_mode ?? false) ? 'pending' : 'ready'}>
                      Caution mode {(extendedPaperRunStatus?.caution_mode ?? extendedPaperRunLaunch?.caution_mode ?? false) ? 'ON' : 'OFF'}
                    </StatusBadge>
                  </div>
                  {extendedPaperRunReasonCodes.length > 0 ? (
                    <div className="subsection">
                      <p className="section-label">Reason codes</p>
                      <div className="button-row">
                        {extendedPaperRunReasonCodes.slice(0, 6).map((code) => (
                          <StatusBadge key={code} tone="neutral">{formatReasonCode(code)}</StatusBadge>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {extendedPaperRunStartError ? <p className="warning-text">{extendedPaperRunStartError}</p> : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={extendedPaperRunStartLoading}
                      onClick={() => void startExtendedPaperRunFromCockpit()}
                    >
                      {extendedPaperRunStartLoading ? 'Starting…' : 'Start extended run'}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={extendedPaperRunStatusLoading || extendedPaperRunStartLoading}
                      onClick={() => void loadExtendedPaperRunStatus()}
                    >
                      Refresh extended status
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Recent compact evidence"
                  title="Live Paper Trial History"
                  description="Recent compact run history for quick operational comparison of V1 trial outcomes."
                >
                  {livePaperTrialHistoryLoading ? <p>Loading live paper trial history…</p> : null}
                  {!livePaperTrialHistoryLoading && livePaperTrialHistoryError ? <p className="warning-text">{livePaperTrialHistoryError}</p> : null}
                  {!livePaperTrialHistoryLoading && !livePaperTrialHistoryError && livePaperTrialHistory ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromTrialStatus(livePaperTrialHistory.latest_trial_status ?? 'IDLE')}>
                          {livePaperTrialHistory.latest_trial_status ?? 'IDLE'}
                        </StatusBadge>
                        <StatusBadge tone="neutral">{livePaperTrialHistory.count} runs</StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>History summary</span><strong>{livePaperTrialHistory.history_summary}</strong></li>
                      </ul>
                      {livePaperTrialHistoryItems.length > 0 ? (
                        <div className="subsection">
                          <p className="section-label">Latest runs</p>
                          <ul className="key-value-list">
                            {livePaperTrialHistoryItems.map((item) => (
                              <li key={`${item.created_at}-${item.trial_status}`}>
                                <span>{formatDate(item.created_at)} · {item.trial_status}</span>
                                <strong>{item.trial_summary || item.next_action_hint || 'n/a'}</strong>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <p className="muted-text">No trial history yet.</p>
                      )}
                    </>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={livePaperTrialHistoryLoading || livePaperTrialRequestLoading}
                      onClick={() => void loadLivePaperTrialHistory()}
                    >
                      Refresh history
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="V1 readiness"
                  title="Live Paper Validation"
                  description="Compact digest to answer if the read-only paper V1 loop is operational now."
                >
                  {livePaperValidationLoading ? <p>Loading live paper validation…</p> : null}
                  {!livePaperValidationLoading && livePaperValidationError ? <p className="warning-text">Live paper validation unavailable.</p> : null}
                  {!livePaperValidationLoading && livePaperValidation ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromValidationStatus(livePaperValidation.validation_status)}>
                          {livePaperValidation.validation_status}
                        </StatusBadge>
                        <StatusBadge tone={livePaperValidation.session_active ? 'ready' : 'pending'}>
                          Session {livePaperValidation.session_active ? 'active' : 'inactive'}
                        </StatusBadge>
                        <StatusBadge tone={livePaperValidation.heartbeat_active ? 'ready' : 'pending'}>
                          Heartbeat {livePaperValidation.heartbeat_active ? 'active' : 'inactive'}
                        </StatusBadge>
                        <StatusBadge tone={toneFromStatus(livePaperValidation.attention_mode)}>
                          Attention {livePaperValidation.attention_mode}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Validation summary</span><strong>{livePaperValidation.validation_summary}</strong></li>
                        <li><span>Next action hint</span><strong>{livePaperValidation.next_action_hint}</strong></li>
                        <li><span>Paper account ready</span><strong>{String(livePaperValidation.paper_account_ready)}</strong></li>
                        <li><span>Portfolio snapshot ready</span><strong>{String(livePaperValidation.portfolio_snapshot_ready)}</strong></li>
                        <li><span>Market data ready</span><strong>{String(livePaperValidation.market_data_ready)}</strong></li>
                      </ul>
                      <div className="subsection">
                        <p className="section-label">Compact checks</p>
                        <div className="button-row">
                          {livePaperValidation.checks.slice(0, 6).map((check) => (
                            <StatusBadge key={check.check_name} tone={toneFromValidationCheck(check.status)}>
                              {check.status} · {check.check_name}
                            </StatusBadge>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : null}
                  <div className="button-row">
                    <button className="secondary-button" type="button" disabled={livePaperValidationLoading} onClick={() => void refreshLivePaperValidation()}>
                      Refresh validation
                    </button>
                    <button className="ghost-button" type="button" onClick={() => navigate('/mission-control')}>Open autopilot</button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="V1 smoke runner"
                  title="Live Paper Smoke Test"
                  description="Short, repeatable V1 paper validation run (real market data read-only + fake money only)."
                >
                  {livePaperSmokeStatusLoading ? <p>Loading smoke test status…</p> : null}
                  {!livePaperSmokeStatusLoading && livePaperSmokeStatusError === 'No smoke test result yet' ? (
                    <p className="muted-text">No smoke test result yet.</p>
                  ) : null}
                  {!livePaperSmokeStatusLoading && livePaperSmokeStatusError && livePaperSmokeStatusError !== 'No smoke test result yet' ? (
                    <p className="warning-text">Live paper smoke test unavailable.</p>
                  ) : null}
                  {livePaperSmokeStatus ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromSmokeStatus(livePaperSmokeStatus.smoke_test_status)}>
                          {livePaperSmokeStatus.smoke_test_status}
                        </StatusBadge>
                        <StatusBadge tone={toneFromValidationStatus(livePaperSmokeStatus.validation_status_after)}>
                          Validation after {livePaperSmokeStatus.validation_status_after}
                        </StatusBadge>
                        <StatusBadge tone="neutral">
                          Heartbeat passes {livePaperSmokeStatus.heartbeat_passes_completed}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Executed at</span><strong>{formatDate(livePaperSmokeStatus.executed_at)}</strong></li>
                        <li><span>Smoke summary</span><strong>{livePaperSmokeStatus.smoke_test_summary}</strong></li>
                        <li><span>Next action hint</span><strong>{livePaperSmokeStatus.next_action_hint}</strong></li>
                        <li><span>Validation status before</span><strong>{livePaperSmokeRunResult?.validation_status_before ?? 'n/a (available after running from cockpit)'}</strong></li>
                        <li><span>Validation status after</span><strong>{livePaperSmokeRunResult?.validation_status_after ?? livePaperSmokeStatus.validation_status_after}</strong></li>
                        <li><span>Heartbeat passes completed</span><strong>{livePaperSmokeRunResult?.heartbeat_passes_completed ?? livePaperSmokeStatus.heartbeat_passes_completed}</strong></li>
                        <li><span>Recent activity detected</span><strong>{livePaperSmokeRunResult ? String(livePaperSmokeRunResult.recent_activity_detected) : 'n/a (available after running from cockpit)'}</strong></li>
                        <li><span>Recent trades detected</span><strong>{livePaperSmokeRunResult ? String(livePaperSmokeRunResult.recent_trades_detected) : 'n/a (available after running from cockpit)'}</strong></li>
                      </ul>
                      <div className="subsection">
                        <p className="section-label">Checks</p>
                        {livePaperSmokeRunResult?.checks.length ? (
                          <ul className="key-value-list">
                            {livePaperSmokeRunResult.checks.map((check) => (
                              <li key={check.check_name}>
                                <span>{check.check_name}</span>
                                <strong>
                                  <StatusBadge tone={toneFromSmokeStatus(check.status)}>{check.status}</StatusBadge> {check.summary}
                                </strong>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="muted-text">Checks will appear after running smoke test from cockpit.</p>
                        )}
                      </div>
                    </>
                  ) : null}
                  {livePaperSmokeRunResult ? (
                    <p className={livePaperSmokeRunResult.smoke_test_status === 'FAIL' ? 'error-text' : livePaperSmokeRunResult.smoke_test_status === 'WARN' ? 'warning-text' : 'success-text'}>
                      {livePaperSmokeRunResult.smoke_test_status}: {livePaperSmokeRunResult.smoke_test_summary}
                    </p>
                  ) : null}
                  {livePaperSmokeRunError ? <p className="warning-text">{livePaperSmokeRunError}</p> : null}
                  <div className="button-row">
                    <button className="secondary-button" type="button" disabled={livePaperSmokeRunLoading} onClick={() => void runLivePaperSmokeTestFromCockpit()}>
                      {livePaperSmokeRunLoading ? 'Running…' : 'Run smoke test'}
                    </button>
                    <button className="ghost-button" type="button" disabled={livePaperSmokeStatusLoading || livePaperSmokeRunLoading} onClick={() => void loadLivePaperSmokeTestStatus()}>
                      Refresh smoke result
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Autonomy flow"
                  title="Autonomy Funnel"
                  description="Compact scan → research → prediction → risk → paper execution snapshot for live read-only + paper-only autonomy."
                >
                  {livePaperAutonomyFunnelLoading ? <p>Loading autonomy funnel…</p> : null}
                  {!livePaperAutonomyFunnelLoading && livePaperAutonomyFunnelError ? <p className="warning-text">Autonomy funnel unavailable.</p> : null}
                  {!livePaperAutonomyFunnelLoading && livePaperAutonomyFunnel ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={toneFromFunnelStatus(livePaperAutonomyFunnel.funnel_status)}>
                          {livePaperAutonomyFunnel.funnel_status}
                        </StatusBadge>
                        <StatusBadge tone="neutral">window {livePaperAutonomyFunnel.window_minutes}m</StatusBadge>
                        <StatusBadge tone="neutral">top stage {livePaperAutonomyFunnel.top_stage}</StatusBadge>
                        <StatusBadge tone={livePaperAutonomyFunnel.stalled_stage ? 'pending' : 'ready'}>
                          stalled {livePaperAutonomyFunnel.stalled_stage ?? 'none'}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Funnel summary</span><strong>{livePaperAutonomyFunnel.funnel_summary}</strong></li>
                        <li><span>Next action hint</span><strong>{livePaperAutonomyFunnel.next_action_hint}</strong></li>
                        <li><span>Scan candidates</span><strong>{livePaperAutonomyFunnel.scan_count}</strong></li>
                        <li><span>Research pursued</span><strong>{livePaperAutonomyFunnel.research_count}</strong></li>
                        <li><span>Prediction evaluated</span><strong>{livePaperAutonomyFunnel.prediction_count}</strong></li>
                        <li><span>Risk approved</span><strong>{livePaperAutonomyFunnel.risk_approved_count}</strong></li>
                        <li><span>Risk blocked</span><strong>{livePaperAutonomyFunnel.risk_blocked_count}</strong></li>
                        <li><span>Paper executions</span><strong>{livePaperAutonomyFunnel.paper_execution_count}</strong></li>
                        <li><span>Recent paper trades</span><strong>{livePaperAutonomyFunnel.recent_trades_count}</strong></li>
                      </ul>
                      <div className="subsection">
                        <p className="section-label">Stages</p>
                        <div className="button-row">
                          {livePaperAutonomyFunnel.stages.map((stage) => (
                            <StatusBadge key={stage.stage_name} tone={toneFromFunnelStatus(stage.status === 'EMPTY' ? 'STALLED' : stage.status === 'LOW' ? 'THIN_FLOW' : 'ACTIVE')}>
                              {stage.stage_name} · {stage.status} · {stage.count}
                            </StatusBadge>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : null}
                  <div className="button-row">
                    <button className="secondary-button" type="button" disabled={livePaperAutonomyFunnelLoading} onClick={() => void loadLivePaperAutonomyFunnel()}>
                      Refresh funnel
                    </button>
                  </div>
                </SectionCard>
                <SectionCard
                  eyebrow="Operational snapshot"
                  title="Operational Snapshot"
                  description="Compact live view of autonomous heartbeat, operator attention, and tuning alert bridge hints."
                >
                  {livePaperOperationalSnapshotLoading ? <p>Loading operational snapshot…</p> : null}
                  {livePaperOperationalSnapshotError ? <p className="error-text">{livePaperOperationalSnapshotError}</p> : null}
                  {!livePaperOperationalSnapshotLoading && !livePaperOperationalSnapshotError && livePaperStatus ? (
                    <>
                      <div className="button-row">
                        <StatusBadge tone={livePaperStatus.session_active ? 'ready' : 'pending'}>
                          Session {livePaperStatus.session_active ? 'active' : 'inactive'}
                        </StatusBadge>
                        <StatusBadge tone={livePaperStatus.heartbeat_active ? 'ready' : 'pending'}>
                          Heartbeat {livePaperStatus.heartbeat_active ? 'active' : 'inactive'}
                        </StatusBadge>
                        {livePaperStatus.operator_attention_hint ? (
                          <StatusBadge tone={toneFromStatus(livePaperStatus.session_active ? 'READY' : 'CAUTION')}>
                            {livePaperStatus.operator_attention_hint.toLowerCase().includes('paused') ? 'Operator attention' : 'No operator attention'}
                          </StatusBadge>
                        ) : null}
                        <StatusBadge tone={livePaperAttentionStatus?.last_auto_sync?.attempted || autonomousHeartbeatSummary?.live_paper_attention_sync?.attempted ? 'ready' : 'neutral'}>
                          {livePaperAttentionStatus?.last_auto_sync?.attempted || autonomousHeartbeatSummary?.live_paper_attention_sync?.attempted
                            ? 'Auto-sync available'
                            : 'Auto-sync unavailable'}
                        </StatusBadge>
                      </div>
                      <ul className="key-value-list">
                        <li><span>Current session status</span><strong>{livePaperStatus.current_session_status}</strong></li>
                        <li><span>Last heartbeat</span><strong>{formatDate(autonomousHeartbeatSummary?.runner_state.last_heartbeat_at)}</strong></li>
                        <li><span>Last successful pass</span><strong>{formatDate(autonomousHeartbeatSummary?.runner_state.last_successful_run_at)}</strong></li>
                        <li><span>Latest heartbeat run</span><strong>{latestAutonomousHeartbeatRun ? `#${latestAutonomousHeartbeatRun.id} · ${latestAutonomousHeartbeatRun.recommendation_summary}` : 'n/a'}</strong></li>
                        <li><span>Latest heartbeat outcome</span><strong>{latestAutonomousHeartbeatRun ? `executed=${latestAutonomousHeartbeatRun.executed_tick_count} blocked=${latestAutonomousHeartbeatRun.blocked_count} wait=${latestAutonomousHeartbeatRun.wait_count}` : 'n/a'}</strong></li>
                        <li><span>Operator hint</span><strong>{livePaperStatus.operator_attention_hint || 'n/a'}</strong></li>
                        <li><span>Auto-sync hint</span><strong>{heartbeatAutoSyncHint}</strong></li>
                        <li><span>Status summary</span><strong>{livePaperStatus.status_summary}</strong></li>
                      </ul>
                      <div className="subsection">
                        <p className="section-label">Operational attention</p>
                        <div className="button-row">
                          <StatusBadge tone={livePaperAttentionStatus?.last_auto_sync?.attempted || autonomousHeartbeatSummary?.live_paper_attention_sync?.attempted ? 'ready' : 'neutral'}>
                            {livePaperAttentionStatus?.last_auto_sync?.attempted || autonomousHeartbeatSummary?.live_paper_attention_sync?.attempted
                              ? 'Heartbeat auto-sync'
                              : 'Auto-sync unavailable'}
                          </StatusBadge>
                          <StatusBadge tone={livePaperAttentionStatus?.active_alert_present ? 'pending' : 'neutral'}>
                            {livePaperAttentionStatus?.active_alert_present ? 'Alert active' : 'No active alert'}
                          </StatusBadge>
                          {livePaperAttentionStatus?.attention_mode ? (
                            <StatusBadge tone={toneFromStatus(livePaperAttentionStatus.attention_mode)}>
                              Mode {livePaperAttentionStatus.attention_mode}
                            </StatusBadge>
                          ) : null}
                          {livePaperAttentionStatus?.funnel_status ? (
                            <StatusBadge tone={toneFromAttentionFunnelStatus(livePaperAttentionStatus.funnel_status)}>
                              Funnel {livePaperAttentionStatus.funnel_status}
                            </StatusBadge>
                          ) : null}
                        </div>
                        {livePaperAttentionStatusError ? <p className="muted-text">Operational attention unavailable</p> : null}
                        <p className="muted-text">
                          Last auto-sync: {livePaperAttentionStatus?.last_auto_sync?.alert_action ?? autonomousHeartbeatSummary?.live_paper_attention_sync?.alert_action ?? 'n/a'}
                        </p>
                        <p className="muted-text">
                          {livePaperAttentionStatus?.last_auto_sync?.sync_summary
                            ?? autonomousHeartbeatSummary?.live_paper_attention_sync?.sync_summary
                            ?? livePaperAttentionStatus?.status_summary
                            ?? 'Attention auto-sync unavailable'}
                        </p>
                        {livePaperAttentionStatus?.stalled_stage ? <p className="muted-text">Stalled at: {livePaperAttentionStatus.stalled_stage}</p> : null}
                        {!livePaperAttentionStatus?.stalled_stage && livePaperAttentionStatus?.top_stage ? <p className="muted-text">Top stage: {livePaperAttentionStatus.top_stage}</p> : null}
                        {livePaperAttentionStatus?.funnel_summary ? <p className="muted-text">{livePaperAttentionStatus.funnel_summary}</p> : null}
                        {!livePaperAttentionStatusError && attentionFunnelUnavailable ? <p className="muted-text">Funnel context unavailable</p> : null}
                        <ul className="key-value-list">
                          <li><span>Auto-sync success</span><strong>{String(livePaperAttentionStatus?.last_auto_sync?.success ?? autonomousHeartbeatSummary?.live_paper_attention_sync?.success ?? false)}</strong></li>
                          <li><span>Active alert severity</span><strong>{livePaperAttentionStatus?.active_alert_severity ?? 'n/a'}</strong></li>
                          <li><span>Status summary</span><strong>{livePaperAttentionStatus?.status_summary ?? 'Attention auto-sync unavailable'}</strong></li>
                        </ul>
                        <div className="button-row">
                          <button
                            className="secondary-button"
                            type="button"
                            disabled={livePaperAttentionSyncLoading}
                            onClick={() => void syncLivePaperAttentionAlertManual()}
                          >
                            {livePaperAttentionSyncLoading ? 'Syncing…' : 'Sync attention alert'}
                          </button>
                        </div>
                        {livePaperAttentionSyncMessage ? <p className="success-text">{livePaperAttentionSyncMessage}</p> : null}
                        {livePaperAttentionSyncError ? <p className="warning-text">{livePaperAttentionSyncError}</p> : null}
                      </div>
                    </>
                  ) : null}
                </SectionCard>
                {livePaperStartResult ? (
                  <p className={livePaperStartResult.bootstrap_action === 'BLOCKED' || livePaperStartResult.bootstrap_action === 'FAILED' ? 'error-text' : 'success-text'}>
                    {livePaperStartResult.bootstrap_action}: {livePaperStartResult.bootstrap_summary} {livePaperStartResult.next_step_summary}
                  </p>
                ) : null}
                {livePaperStartError ? <p className="error-text">{livePaperStartError}</p> : null}
                <div className="button-row">
                  <button className="primary-button" type="button" disabled={livePaperStartLoading} onClick={() => void startLivePaperAutopilot()}>
                    {livePaperStartLoading ? 'Starting…' : 'Start live paper autopilot'}
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={livePaperStatusLoading || livePaperOperationalSnapshotLoading || livePaperValidationLoading || livePaperAutonomyFunnelLoading}
                    onClick={() => {
                      void Promise.all([
                        loadLivePaperStatus(),
                        loadLivePaperOperationalSnapshot(),
                        loadPaperPortfolioSnapshot(),
                        loadLivePaperValidation(),
                        loadLivePaperSmokeTestStatus(),
                        loadLivePaperAutonomyFunnel(),
                      ]);
                    }}
                  >
                    Refresh status
                  </button>
                </div>
              </SectionCard>

              <SectionCard eyebrow="Mission control & operations" title="Cycle posture and impact" description="Mission status, cycle context, and operational incidents.">
                <ul className="key-value-list">
                  <li><span>Mission status</span><strong>{snapshot.missionControl?.state.status ?? 'n/a'}</strong></li>
                  <li><span>Last heartbeat</span><strong>{formatDate(snapshot.missionControl?.state.last_heartbeat_at)}</strong></li>
                  <li><span>Latest cycle status</span><strong>{snapshot.missionControl?.latest_cycle?.status ?? 'n/a'}</strong></li>
                  <li><span>Latest cycle summary</span><strong>{snapshot.missionControl?.latest_cycle?.summary ?? 'n/a'}</strong></li>
                  <li><span>Open incidents</span><strong>{snapshot.incidents?.summary.active_incidents ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/mission-control')}>Open mission control</button><button className="secondary-button" type="button" onClick={() => navigate('/incidents')}>Open incidents</button></div>
              </SectionCard>

              <SectionCard eyebrow="Risk & exposure" title="Portfolio governance and position review" description="Open exposure, throttle state, and decisions requiring manual attention.">
                <ul className="key-value-list">
                  <li><span>Governor state</span><strong>{snapshot.portfolioGovernor?.latest_throttle_state ?? 'n/a'}</strong></li>
                  <li><span>Open positions</span><strong>{snapshot.portfolioGovernor?.open_positions ?? 0}</strong></li>
                  <li><span>Throttle decision</span><strong>{snapshot.portfolioThrottle?.state ?? 'n/a'}</strong></li>
                  <li><span>Review required</span><strong>{snapshot.positionDecisions.filter((item) => item.status === 'REVIEW_REQUIRED').length}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/portfolio-governor')}>Open portfolio governor</button><button className="secondary-button" type="button" onClick={() => navigate('/positions')}>Open positions</button></div>
              </SectionCard>

              <SectionCard eyebrow="Execution & venue" title="Bridge, parity and account reconciliation" description="Snapshot of sandbox execution readiness and parity quality.">
                <ul className="key-value-list">
                  <li><span>Bridge validations</span><strong>{snapshot.brokerBridge?.validated ?? 0}</strong></li>
                  <li><span>Bridge rejects</span><strong>{snapshot.brokerBridge?.rejected ?? 0}</strong></li>
                  <li><span>Parity gaps</span><strong>{snapshot.executionVenue?.parity_gap ?? 0}</strong></li>
                  <li><span>Reconciliation mismatches</span><strong>{snapshot.venueAccount?.latest_reconciliation?.mismatches_count ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/broker-bridge')}>Open bridge</button><button className="secondary-button" type="button" onClick={() => navigate('/execution-venue')}>Open venue</button><button className="secondary-button" type="button" onClick={() => navigate('/venue-account')}>Open account</button></div>
              </SectionCard>


              <SectionCard eyebrow="Runbooks" title="Guided remediation workflows" description="Manual-first playbook coverage for incidents, degradations and recurring operator procedures.">
                <ul className="key-value-list">
                  <li><span>Open</span><strong>{snapshot.runbookSummary?.counts.open ?? 0}</strong></li>
                  <li><span>In progress</span><strong>{snapshot.runbookSummary?.counts.in_progress ?? 0}</strong></li>
                  <li><span>Blocked</span><strong>{snapshot.runbookSummary?.counts.blocked ?? 0}</strong></li>
                  <li><span>Autopilot paused</span><strong>{snapshot.runbookAutopilotSummary?.counts.paused_for_approval ?? 0}</strong></li>
                  <li><span>Autopilot blocked</span><strong>{snapshot.runbookAutopilotSummary?.counts.blocked ?? 0}</strong></li>
                  <li><span>Autopilot completed</span><strong>{snapshot.runbookAutopilotSummary?.counts.completed ?? 0}</strong></li>
                  <li><span>Approval center pending</span><strong>{snapshot.approvalSummary?.pending ?? 0}</strong></li>
                  <li><span>High priority approvals</span><strong>{snapshot.approvalSummary?.high_priority_pending ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/runbooks')}>Open runbooks</button><button className="ghost-button" type="button" onClick={() => navigate('/approvals')}>Open approvals</button><button className="ghost-button" type="button" onClick={() => navigate('/trust-calibration')}>Open trust calibration</button><button className="ghost-button" type="button" onClick={() => navigate('/policy-tuning')}>Open policy tuning</button></div>
              </SectionCard>

              <SectionCard eyebrow="Scan intelligence" title="Narrative scan summary" description="Compact scan-agent filter summary for quick handoff posture checks.">
                <ul className="key-value-list">
                  <li><span>Signals</span><strong>{scanSummary?.signal_count ?? 0}</strong></li>
                  <li><span>Shortlisted</span><strong>{scanSummary?.shortlisted_signal_count ?? 0}</strong></li>
                  <li><span>Watch</span><strong>{scanSummary?.watch_signal_count ?? 0}</strong></li>
                  <li><span>Ignored</span><strong>{scanSummary?.ignored_signal_count ?? 0}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/scan-agent')}>Open scan agent board</button></div>
              </SectionCard>

              <SectionCard eyebrow="Change governance" title="Promotion, rollout and champion/challenger" description="Current promotion recommendations and rollout status.">
                <ul className="key-value-list">
                  <li><span>Promotion recommendation</span><strong>{snapshot.promotionSummary?.latest_run?.recommendation_code ?? 'n/a'}</strong></li>
                  <li><span>Rollout status</span><strong>{snapshot.rollout?.current_run?.status ?? snapshot.rollout?.latest_run?.status ?? 'n/a'}</strong></li>
                  <li><span>Policy rollout observing</span><strong>{snapshot.policyRolloutSummary?.observing_runs ?? 0}</strong></li>
                  <li><span>Policy rollback recommended</span><strong>{snapshot.policyRolloutSummary?.rollback_recommended_runs ?? 0}</strong></li>
                  <li><span>Champion/challenger mode</span><strong>{snapshot.championChallengerSummary?.latest_run?.status ?? 'n/a'}</strong></li>
                  <li><span>Champion/challenger result</span><strong>{snapshot.championChallengerSummary?.latest_run?.recommendation_code ?? 'n/a'}</strong></li>
                  <li><span>Autonomy pending changes</span><strong>{snapshot.autonomySummary?.pending_stage_changes ?? 0}</strong></li>
                  <li><span>Autonomy degraded/blocked</span><strong>{(snapshot.autonomySummary?.degraded_domains ?? 0) + (snapshot.autonomySummary?.blocked_domains ?? 0)}</strong></li><li><span>Autonomy rollout observing</span><strong>{snapshot.autonomyRolloutSummary?.observing_runs ?? 0}</strong></li><li><span>Autonomy freeze/rollback warnings</span><strong>{(snapshot.autonomyRolloutSummary?.freeze_recommended_runs ?? 0) + (snapshot.autonomyRolloutSummary?.rollback_recommended_runs ?? 0)}</strong></li><li><span>Roadmap blocked domains</span><strong>{snapshot.autonomyRoadmapSummary?.latest_blocked_domains.length ?? 0}</strong></li><li><span>Active campaigns</span><strong>{snapshot.autonomyCampaignSummary?.active_campaigns ?? 0}</strong></li><li><span>Latest campaign status</span><strong>{snapshot.autonomyCampaignSummary?.latest_status ?? 'n/a'}</strong></li><li><span>Roadmap next best sequence</span><strong>{snapshot.autonomyRoadmapSummary?.latest_recommended_sequence.slice(0, 2).join(' → ') || 'n/a'}</strong></li><li><span>Scenario best next move</span><strong>{autonomyScenarioSummary?.latest_selected_option_key ?? 'n/a'}</strong></li><li><span>Scenario recommendation</span><strong>{autonomyScenarioSummary?.latest_recommendation_code ?? 'n/a'}</strong></li>
                </ul>
                <div className="button-row"><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open promotion</button><button className="secondary-button" type="button" onClick={() => navigate('/certification')}>Open certification</button><button className="secondary-button" type="button" onClick={() => navigate('/promotion')}>Open rollout execution board</button><button className="secondary-button" type="button" onClick={() => navigate('/rollout')}>Open rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/policy-rollout')}>Open policy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy')}>Open autonomy</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-rollout')}>Open autonomy rollout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-roadmap')}>Open autonomy roadmap</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scenarios')}>Open autonomy scenarios</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-program')}>Open autonomy program</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-scheduler')}>Open autonomy scheduler</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-launch')}>Open autonomy launch</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-activation')}>Open autonomy activation</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-operations')}>Open autonomy operations</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-interventions')}>Open autonomy interventions</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-recovery')}>Open autonomy recovery</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-disposition')}>Open autonomy disposition</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-closeout')}>Open autonomy closeout</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-followup')}>Open autonomy followup</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-feedback')}>Open autonomy feedback</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-insights')}>Open autonomy insights</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory')}>Open autonomy advisory</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-advisory-resolution')}>Open advisory resolution</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-backlog')}>Open autonomy backlog</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-intake')}>Open autonomy intake</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-planning-review')}>Open planning review</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-decision')}>Open autonomy decision</button><button className="secondary-button" type="button" onClick={() => navigate('/autonomy-package-review')}>Open package review</button><button className="secondary-button" type="button" onClick={() => navigate('/champion-challenger')}>Open C/C</button></div>
              </SectionCard>
            </div>

            <SectionCard eyebrow="Attention queue" title="Prioritized attention and trace drill-down" description="Severity-first queue across incidents, parity, queue pressure, and blocked opportunities.">
              {attention.length === 0 ? <EmptyState eyebrow="Atención" title="Sin alertas urgentes" description="No hay bloqueos críticos en este momento. Continúa con monitoreo normal." /> : (
                <div className="cockpit-attention-list">
                  {attention.map((item) => (
                    <article key={item.id} className="cockpit-attention-item">
                      <div>
                        <p className="section-label">{item.severity}</p>
                        <h3>{item.title}</h3>
                        <p>{item.summary}</p>
                      </div>
                      <div className="button-row">
                        <button className="secondary-button" type="button" onClick={() => navigate(item.route)}>Open module</button>
                        <TraceButton item={item} />
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard
              eyebrow="Runtime tuning"
              title="Runtime Tuning Review Queue"
              description="Compact human-review queue combining manual review state with existing technical attention priority."
            >
              <div className="button-row">
                <label className="muted-text">
                  <input
                    type="checkbox"
                    checked={reviewQueueUnresolvedOnly}
                    onChange={(event) => setReviewQueueUnresolvedOnly(event.target.checked)}
                  />{' '}
                  Unresolved only
                </label>
                <label className="muted-text">
                  Status:{' '}
                  <select value={reviewQueueStatusFilter} onChange={(event) => setReviewQueueStatusFilter(event.target.value as RuntimeTuningReviewState['effective_review_status'] | 'ALL')}>
                    <option value="ALL">All</option>
                    <option value="UNREVIEWED">UNREVIEWED</option>
                    <option value="FOLLOWUP_REQUIRED">FOLLOWUP_REQUIRED</option>
                    <option value="STALE_REVIEW">STALE_REVIEW</option>
                    <option value="ACKNOWLEDGED_CURRENT">ACKNOWLEDGED_CURRENT</option>
                  </select>
                </label>
                <label className="muted-text">
                  Aging:{' '}
                  <select value={reviewQueueAgeBucketFilter} onChange={(event) => setReviewQueueAgeBucketFilter(event.target.value as 'ALL' | 'FRESH' | 'AGING' | 'OVERDUE')}>
                    <option value="ALL">All</option>
                    <option value="OVERDUE">OVERDUE</option>
                    <option value="AGING">AGING</option>
                    <option value="FRESH">FRESH</option>
                  </select>
                </label>
                <label className="muted-text">
                  <input
                    type="checkbox"
                    checked={reviewEscalatedOnly}
                    onChange={(event) => setReviewEscalatedOnly(event.target.checked)}
                  />{' '}
                  Escalated only
                </label>
                <label className="muted-text">
                  Escalation:{' '}
                  <select value={reviewEscalationLevelFilter} onChange={(event) => setReviewEscalationLevelFilter(event.target.value as 'ALL' | 'MONITOR' | 'ELEVATED' | 'URGENT')}>
                    <option value="ALL">All</option>
                    <option value="URGENT">URGENT</option>
                    <option value="ELEVATED">ELEVATED</option>
                    <option value="MONITOR">MONITOR</option>
                  </select>
                </label>
                <label className="muted-text">
                  Activity action:{' '}
                  <select
                    value={reviewActivityActionTypeFilter}
                    onChange={(event) => setReviewActivityActionTypeFilter(event.target.value as RuntimeTuningReviewAction['action_type'] | 'ALL')}
                  >
                    <option value="ALL">All</option>
                    <option value="ACKNOWLEDGE_CURRENT">ACKNOWLEDGE_CURRENT</option>
                    <option value="MARK_FOLLOWUP_REQUIRED">MARK_FOLLOWUP_REQUIRED</option>
                    <option value="CLEAR_REVIEW_STATE">CLEAR_REVIEW_STATE</option>
                  </select>
                </label>
                <label className="muted-text">
                  Activity limit:{' '}
                  <select value={reviewActivityLimit} onChange={(event) => setReviewActivityLimit(Number(event.target.value))}>
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                  </select>
                </label>
              </div>
              {reviewQueueError ? <p className="warning-text">{reviewQueueError}</p> : null}
              {!reviewQueue ? null : (
                <>
                  {!autotriageDigest ? null : (
                    <div className="subsection">
                      <p className="section-label">Autotriage Digest</p>
                      <ul className="key-value-list">
                        <li><span>Human attention mode</span><strong>{autotriageDigest.human_attention_mode}</strong></li>
                        <li><span>Requires human now</span><strong>{String(autotriageDigest.requires_human_now)}</strong></li>
                        <li><span>Can defer human review</span><strong>{String(autotriageDigest.can_defer_human_review)}</strong></li>
                        <li><span>Unresolved</span><strong>{autotriageDigest.unresolved_count}</strong></li>
                        <li><span>Urgent</span><strong>{autotriageDigest.urgent_count}</strong></li>
                        <li><span>Overdue</span><strong>{autotriageDigest.overdue_count}</strong></li>
                        <li><span>Recent activity</span><strong>{autotriageDigest.recent_activity_count}</strong></li>
                        <li><span>Next recommended scope</span><strong>{autotriageDigest.next_recommended_scope ?? 'n/a'}</strong></li>
                      </ul>
                      <p className={autotriageDigest.requires_human_now ? 'warning-text' : 'muted-text'}>{autotriageDigest.autotriage_summary}</p>
                      {!autotriageAlertStatus ? null : (
                        <div className="subsection">
                          <p className="section-label">Attention alert bridge</p>
                          <ul className="key-value-list">
                            <li><span>Signal</span><strong>{autotriageAlertStatus.active_alert_present ? 'Alert active' : 'No active alert'}</strong></li>
                            <li><span>Severity</span><strong>{autotriageAlertStatus.active_alert_severity ?? 'n/a'}</strong></li>
                            <li><span>Next recommended scope</span><strong>{autotriageAlertStatus.next_recommended_scope ?? 'n/a'}</strong></li>
                            <li><span>Status summary</span><strong>{autotriageAlertStatus.status_summary}</strong></li>
                            <li><span>Last sync</span><strong>{autotriageAlertStatus.last_alert_action ?? autotriageAlertStatus.runtime_tuning_attention_sync?.alert_action ?? 'n/a'}</strong></li>
                            <li><span>Material change</span><strong>{String(autotriageAlertStatus.material_change_detected ?? autotriageAlertStatus.runtime_tuning_attention_sync?.material_change_detected ?? false)}</strong></li>
                            <li><span>Update suppressed</span><strong>{String(autotriageAlertStatus.runtime_tuning_attention_sync?.update_suppressed ?? false)}</strong></li>
                            {(autotriageAlertStatus.runtime_tuning_attention_sync?.material_change_fields?.length ?? 0) > 0 ? (
                              <li>
                                <span>Changed fields</span>
                                <strong>{autotriageAlertStatus.runtime_tuning_attention_sync?.material_change_fields.join(', ')}</strong>
                              </li>
                            ) : null}
                            {autotriageAlertStatus.runtime_tuning_attention_sync?.suppression_reason ? (
                              <li><span>Suppression reason</span><strong>{autotriageAlertStatus.runtime_tuning_attention_sync.suppression_reason}</strong></li>
                            ) : null}
                            <li><span>Sync source</span><strong>Manual + heartbeat auto-sync</strong></li>
                          </ul>
                          {autotriageAlertStatus.runtime_tuning_attention_sync?.update_suppressed ? (
                            <p className="muted-text">Alert update suppressed.</p>
                          ) : null}
                          <p className="muted-text">{heartbeatAutoSyncHint}</p>
                          <div className="button-row">
                            <button className="secondary-button" type="button" disabled={autotriageAlertSyncLoading} onClick={() => void syncAutotriageAttentionAlert()}>
                              Sync attention alert
                            </button>
                          </div>
                          {autotriageAlertSyncMessage ? <p className="success-text">{autotriageAlertSyncMessage}</p> : null}
                          {autotriageAlertSyncError ? <p className="warning-text">{autotriageAlertSyncError}</p> : null}
                        </div>
                      )}
                      <div className="button-row">
                        <button
                          className="secondary-button"
                          type="button"
                          disabled={!autotriageDigest.next_recommended_scope}
                          onClick={() => {
                            const nextScope = autotriageDigest.next_recommended_scope;
                            if (!nextScope) return;
                            if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === nextScope)) {
                              void investigateScope(nextScope);
                              return;
                            }
                            setAttentionOnly(false);
                            setQueuedInvestigationScope(nextScope);
                          }}
                        >
                          Open next review
                        </button>
                        <button
                          className="ghost-button"
                          type="button"
                          disabled={!autotriageDigest.next_recommended_scope && autotriageDigest.top_scopes.length === 0}
                          onClick={() => {
                            const nextScope = autotriageDigest.next_recommended_scope;
                            const topScope = autotriageDigest.top_scopes[0];
                            const deepLink = topScope?.runtime_investigation_deep_link ?? (nextScope ? `/runtime?tuningScope=${encodeURIComponent(nextScope)}&investigate=1` : null);
                            if (deepLink) {
                              navigate(deepLink);
                            }
                          }}
                        >
                          Open in runtime
                        </button>
                      </div>
                      {autotriageDigest.top_scopes.length === 0 ? (
                        <p className="muted-text">No top scopes recommended right now.</p>
                      ) : (
                        <div className="cockpit-attention-list">
                          {autotriageDigest.top_scopes.map((item) => (
                            <article key={`autotriage-${item.source_scope}`} className="cockpit-attention-item">
                              <div>
                                <p className="section-label">{item.escalation_level} · {item.effective_review_status} · {item.age_bucket}{typeof item.age_days === 'number' ? ` (${item.age_days}d)` : ''}</p>
                                <h3>{item.source_scope}</h3>
                                <p><strong>{item.attention_priority}</strong> · {item.review_summary}</p>
                                <p className="muted-text">{item.technical_summary}</p>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {!reviewEscalation ? null : (
                    <div className="subsection">
                      <p className="section-label">Review Escalation</p>
                      <ul className="key-value-list">
                        <li><span>Urgent</span><strong>{reviewEscalation.urgent_count}</strong></li>
                        <li><span>Elevated</span><strong>{reviewEscalation.elevated_count}</strong></li>
                        <li><span>Monitor</span><strong>{reviewEscalation.monitor_count}</strong></li>
                        <li><span>Highest escalation scope</span><strong>{reviewEscalation.highest_escalation_scope ?? 'n/a'}</strong></li>
                      </ul>
                      <p className={reviewEscalation.urgent_count > 0 ? 'warning-text' : 'muted-text'}>{reviewEscalation.escalation_summary}</p>
                      {reviewEscalation.items.length === 0 ? (
                        <p className="muted-text">No escalated items for the current filters.</p>
                      ) : (
                        <div className="cockpit-attention-list">
                          {reviewEscalation.items.map((item) => (
                            <article key={`escalation-${item.source_scope}`} className="cockpit-attention-item">
                              <div>
                                <p className="section-label">
                                  #{item.escalation_rank} · {item.escalation_level} · {item.effective_review_status} · {item.age_bucket} ({item.age_days}d)
                                </p>
                                <h3>{item.source_scope}</h3>
                                <p>
                                  <strong>{item.attention_priority}</strong> · {item.review_summary || item.technical_summary}
                                </p>
                                {item.requires_immediate_attention ? <p className="warning-text">Requires immediate attention.</p> : null}
                              </div>
                              <div className="button-row">
                                <button
                                  className="secondary-button"
                                  type="button"
                                  onClick={() => {
                                    if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                      void investigateScope(item.source_scope);
                                      return;
                                    }
                                    setAttentionOnly(false);
                                    setQueuedInvestigationScope(item.source_scope);
                                  }}
                                >
                                  Open review
                                </button>
                                <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {!reviewAging ? null : (
                    <div className="subsection">
                      <p className="section-label">Review Aging</p>
                      <ul className="key-value-list">
                        <li><span>Fresh</span><strong>{reviewAging.fresh_count}</strong></li>
                        <li><span>Aging</span><strong>{reviewAging.aging_count}</strong></li>
                        <li><span>Overdue</span><strong>{reviewAging.overdue_count}</strong></li>
                        <li><span>Highest urgency scope</span><strong>{reviewAging.highest_urgency_scope ?? 'n/a'}</strong></li>
                      </ul>
                      <p className={reviewAging.overdue_count > 0 ? 'warning-text' : 'muted-text'}>{reviewAging.aging_summary}</p>
                    </div>
                  )}
                  {!reviewActivity ? null : (
                    <div className="subsection">
                      <p className="section-label">Recent Review Activity</p>
                      <ul className="key-value-list">
                        <li><span>Recent actions</span><strong>{reviewActivity.activity_count}</strong></li>
                        <li><span>Latest action at</span><strong>{formatDate(reviewActivity.latest_action_at)}</strong></li>
                        <li><span>Summary</span><strong>{reviewActivity.activity_summary}</strong></li>
                      </ul>
                      {reviewActivity.items.length === 0 ? (
                        <p className="muted-text">No review actions match the current activity filters.</p>
                      ) : (
                        <div className="cockpit-attention-list">
                          {reviewActivity.items.map((item, index) => (
                            <article key={`activity-${item.source_scope}-${item.created_at}-${index}`} className="cockpit-attention-item">
                              <div>
                                <p className="section-label">{item.activity_label} · {item.resulting_review_status}</p>
                                <h3>{item.source_scope}</h3>
                                <p>{formatDate(item.created_at)} · {item.action_type}</p>
                                <p className="muted-text">{item.scope_review_summary}</p>
                              </div>
                              <div className="button-row">
                                <button
                                  className="secondary-button"
                                  type="button"
                                  onClick={() => {
                                    if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                      void investigateScope(item.source_scope);
                                      return;
                                    }
                                    setAttentionOnly(false);
                                    setQueuedInvestigationScope(item.source_scope);
                                  }}
                                >
                                  Open review
                                </button>
                                <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <ul className="key-value-list">
                    <li><span>Queue scopes</span><strong>{reviewQueue.queue_count}</strong></li>
                    <li><span>Unreviewed</span><strong>{reviewQueue.unreviewed_count}</strong></li>
                    <li><span>Follow-up</span><strong>{reviewQueue.followup_count}</strong></li>
                    <li><span>Stale</span><strong>{reviewQueue.stale_count}</strong></li>
                  </ul>
                  <p className="muted-text">{reviewQueue.queue_summary}</p>
                  {(reviewAging?.items ?? reviewQueue.items).length === 0 ? (
                    <EmptyState eyebrow="Cola de revisión" title="Sin elementos pendientes" description="No hay ámbitos que coincidan con los filtros actuales." />
                  ) : (
                    <div className="cockpit-attention-list">
                      {(reviewAging?.items ?? reviewQueue.items).map((item) => (
                        <article key={item.source_scope} className="cockpit-attention-item">
                          <div>
                            <p className="section-label">
                              #{isAgingQueueItem(item) ? item.aging_rank : item.queue_rank} · {item.effective_review_status}{' '}
                              {isAgingQueueItem(item) ? `· ${item.age_bucket} (${item.age_days}d)` : null}
                            </p>
                            <h3>{item.source_scope}</h3>
                            <p>
                              <strong>{item.attention_priority}</strong> · {item.review_summary || item.technical_summary}
                            </p>
                            <p className="muted-text">{item.technical_summary}</p>
                            {isAgingQueueItem(item) && item.overdue ? (
                              <p className="warning-text">Overdue review item. Prioritize manual action for this scope.</p>
                            ) : null}
                            {(item.effective_review_status === 'FOLLOWUP_REQUIRED' || item.effective_review_status === 'STALE_REVIEW') ? (
                              <p className="warning-text">Requires explicit human follow-up before this scope is considered current.</p>
                            ) : null}
                          </div>
                            <div className="button-row">
                            <button
                              className="secondary-button"
                              type="button"
                              onClick={() => {
                                if (tuningPanel?.items?.some((panelItem) => panelItem.source_scope === item.source_scope)) {
                                  void investigateScope(item.source_scope);
                                  return;
                                }
                                setAttentionOnly(false);
                                setQueuedInvestigationScope(item.source_scope);
                              }}
                            >
                              Open review
                            </button>
                            <button className="ghost-button" type="button" onClick={() => navigate(item.runtime_investigation_deep_link)}>Open in runtime</button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </>
              )}
            </SectionCard>

            <SectionCard
              eyebrow="Runtime tuning"
              title="Runtime Tuning Attention"
              description="Read-only handoff from runtime_governor review board for high-signal tuning scopes needing operator attention."
            >
              <div className="button-row">
                <label className="muted-text">
                  <input type="checkbox" checked={attentionOnly} onChange={(event) => setAttentionOnly(event.target.checked)} /> Attention only
                </label>
                <button className="secondary-button" type="button" onClick={() => navigate('/runtime')}>Open full runtime view</button>
              </div>
              {tuningPanelError ? <p className="warning-text">{tuningPanelError}</p> : null}
              {!tuningPanel ? null : (
                <>
                  <ul className="key-value-list">
                    <li><span>Scopes needing attention</span><strong>{tuningPanel.attention_scope_count}</strong></li>
                    <li><span>Highest priority scope</span><strong>{tuningPanel.highest_priority_scope ?? 'n/a'}</strong></li>
                    <li><span>Highest priority status</span><strong>{tuningPanel.highest_priority_status ?? 'n/a'}</strong></li>
                  </ul>
                  <p className="muted-text">{tuningPanel.panel_summary}</p>
                  {tuningPanel.items.length === 0 ? (
                    <EmptyState eyebrow="Runtime tuning" title="Sin revisión urgente de tuning" description="Los ámbitos monitoreados se ven estables con el filtro actual." />
                  ) : (
                    <div className="cockpit-attention-list">
                      {tuningPanel.items.map((item) => {
                        const detail = panelDetailCache[item.source_scope];
                        const diff = diffCache[item.source_scope];
                        const isDiffOpen = openDiffScope === item.source_scope;
                        const isRunContextOpen = openRunContextScope === item.source_scope;
                        const isInvestigationOpen = openInvestigationScope === item.source_scope;
                        const investigation = investigationCache[item.source_scope];
                        const timeline = timelineCache[item.source_scope];
                        const timelineLoading = timelineLoadingCache[item.source_scope] ?? false;
                        const timelineError = timelineErrorCache[item.source_scope] ?? null;
                        const timelineOnlyNonStable = timelineOnlyNonStableByScope[item.source_scope] ?? false;
                        const timelineLimit = timelineLimitByScope[item.source_scope] ?? DEFAULT_TIMELINE_LIMIT;
                        const reviewState = reviewStateCache[item.source_scope];
                        const reviewStateError = reviewStateErrorCache[item.source_scope] ?? null;
                        const reviewStatus = reviewState?.effective_review_status ?? 'UNREVIEWED';
                        const reviewActionLoading = reviewActionLoadingByScope[item.source_scope] ?? false;
                        const reviewActionError = reviewActionErrorByScope[item.source_scope] ?? null;
                        return (
                          <article key={item.source_scope} className="cockpit-attention-item">
                            <div>
                              <p className="section-label">{item.attention_priority}</p>
                              <h3>{item.source_scope}</h3>
                              <p>{item.board_summary}</p>
                              <p className="muted-text">
                                <strong>Manual review:</strong>{' '}
                                <StatusBadge tone={toneFromStatus(reviewStatus)}>{REVIEW_STATUS_LABELS[reviewStatus]}</StatusBadge>{' '}
                                · {reviewState?.review_summary ?? REVIEW_STATUS_HINTS[reviewStatus]}
                              </p>
                              <p className="muted-text"><strong>Drift:</strong> {item.drift_status} | <strong>Diff:</strong> {item.latest_diff_summary ?? 'No comparable diff'}</p>
                              {reviewStateError ? <p className="warning-text">{reviewStateError}</p> : null}
                            </div>
                            <div className="button-row">
                              <button className="secondary-button" type="button" onClick={() => navigate(item.runtime_deep_link)}>Open in runtime</button>
                              <button className="secondary-button" type="button" onClick={() => void investigateScope(item.source_scope)}>Investigate</button>
                              <button className="ghost-button" type="button" onClick={() => void viewDiff(item.source_scope, item.latest_diff_snapshot_id)}>View diff</button>
                              <button className="ghost-button" type="button" onClick={() => void viewRunContext(item.source_scope)}>View run context</button>
                            </div>
                            {isInvestigationOpen ? (
                              <div className="subsection">
                                <p className="section-label">Compact investigation</p>
                                {!investigation ? (
                                  <p className="warning-text">Could not load investigation packet.</p>
                                ) : (
                                  <>
                                    <ul className="key-value-list">
                                      <li><span>Scope</span><strong>{investigation.source_scope}</strong></li>
                                      <li><span>Summary</span><strong>{investigation.investigation_summary}</strong></li>
                                      <li><span>Priority</span><strong>{investigation.attention_priority}</strong></li>
                                      <li><span>Alert status</span><strong>{investigation.alert_status}</strong></li>
                                      <li><span>Drift status</span><strong>{investigation.drift_status}</strong></li>
                                      <li><span>Review reason codes</span><strong>{investigation.review_reason_codes.join(', ') || 'n/a'}</strong></li>
                                    </ul>
                                    <div className="subsection">
                                      <p className="section-label">Recent Timeline</p>
                                      <div className="button-row">
                                        <label className="muted-text">
                                          <input
                                            type="checkbox"
                                            checked={timelineOnlyNonStable}
                                            onChange={(event) => {
                                              void loadScopeTimeline(item.source_scope, {
                                                limit: timelineLimit,
                                                onlyNonStable: event.target.checked,
                                              });
                                            }}
                                          />{' '}
                                          Show only non-stable
                                        </label>
                                        <button
                                          className="ghost-button"
                                          type="button"
                                          onClick={() => void loadScopeTimeline(item.source_scope, {
                                            limit: timelineLimit * 2,
                                            onlyNonStable: timelineOnlyNonStable,
                                          })}
                                        >
                                          Show more timeline
                                        </button>
                                      </div>
                                      {timelineLoading ? <p className="muted-text">Loading recent timeline...</p> : null}
                                      {timelineError ? <p className="warning-text">{timelineError}</p> : null}
                                      {!timelineLoading && !timelineError && timeline ? (
                                        <>
                                          <p className="muted-text">{timeline.timeline_summary}</p>
                                          <ul className="key-value-list">
                                            <li><span>Recently stable</span><strong>{timeline.is_recently_stable ? 'Yes' : 'No'}</strong></li>
                                            <li><span>Recent profile shift</span><strong>{timeline.has_recent_profile_shift ? 'Yes' : 'No'}</strong></li>
                                            <li><span>Recent review now</span><strong>{timeline.has_recent_review_now ? 'Yes' : 'No'}</strong></li>
                                          </ul>
                                          <ul className="key-value-list">
                                            {timeline.entries.map((entry) => (
                                              <li key={entry.snapshot_id}>
                                                <span>
                                                  {formatDate(entry.created_at)} · {entry.timeline_label} · {entry.drift_status} / {entry.alert_status}
                                                </span>
                                                <strong>
                                                  {entry.diff_summary || 'No comparable diff summary.'} · Fields {entry.changed_field_count} · Guardrails {entry.changed_guardrail_count}
                                                  {entry.correlated_run_id ? ` · Run ${entry.correlated_run_id}` : ''}
                                                </strong>
                                              </li>
                                            ))}
                                          </ul>
                                        </>
                                      ) : null}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Manual Review</p>
                                      <ul className="key-value-list">
                                        <li><span>effective_review_status</span><strong>{reviewState?.effective_review_status ?? 'UNREVIEWED'}</strong></li>
                                        <li><span>review_summary</span><strong>{reviewState?.review_summary ?? REVIEW_STATUS_HINTS.UNREVIEWED}</strong></li>
                                        <li><span>last_action_type</span><strong>{reviewState?.last_action_type ?? 'n/a'}</strong></li>
                                        <li><span>last_action_at</span><strong>{formatDate(reviewState?.last_action_at)}</strong></li>
                                        <li><span>has_newer_snapshot_than_reviewed</span><strong>{reviewState?.has_newer_snapshot_than_reviewed ? 'Yes' : 'No'}</strong></li>
                                      </ul>
                                      <div className="button-row">
                                        <button className="secondary-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'ACKNOWLEDGE')}>Acknowledge current</button>
                                        <button className="secondary-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'FOLLOWUP')}>Mark follow-up</button>
                                        <button className="ghost-button" type="button" disabled={reviewActionLoading} onClick={() => void runManualReviewAction(item.source_scope, 'CLEAR')}>Clear review state</button>
                                      </div>
                                      {reviewActionError ? <p className="warning-text">{reviewActionError}</p> : null}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Diff preview</p>
                                      {!investigation.has_comparable_diff ? (
                                        <p>No comparable diff.</p>
                                      ) : (
                                        <ul className="key-value-list">
                                          <li><span>Latest diff summary</span><strong>{investigation.latest_diff_summary ?? 'n/a'}</strong></li>
                                          <li><span>Changed fields</span><strong>{investigation.changed_field_count}</strong></li>
                                          <li><span>Changed guardrails</span><strong>{investigation.changed_guardrail_count}</strong></li>
                                          <li><span>Fields preview</span><strong>{investigation.changed_fields_preview.join(', ') || 'n/a'}</strong></li>
                                          <li><span>Guardrail preview</span><strong>{investigation.changed_guardrail_fields_preview.join(', ') || 'n/a'}</strong></li>
                                        </ul>
                                      )}
                                    </div>
                                    <div className="subsection">
                                      <p className="section-label">Run context preview</p>
                                      {!investigation.has_correlated_run ? (
                                        <p>No correlated run.</p>
                                      ) : (
                                        <ul className="key-value-list">
                                          <li><span>Run id</span><strong>{investigation.correlated_run_id}</strong></li>
                                          <li><span>Timestamp</span><strong>{formatDate(investigation.correlated_run_timestamp)}</strong></li>
                                          <li><span>Profile</span><strong>{investigation.correlated_profile_name ?? 'n/a'}</strong></li>
                                          <li><span>Fingerprint</span><strong>{investigation.correlated_profile_fingerprint ?? 'n/a'}</strong></li>
                                        </ul>
                                      )}
                                    </div>
                                    <div className="button-row">
                                      <button className="secondary-button" type="button" onClick={() => navigate(`/runtime?tuningScope=${encodeURIComponent(investigation.source_scope)}&investigate=1`)}>Open full runtime investigation</button>
                                      <button className="ghost-button" type="button" onClick={() => setOpenInvestigationScope(null)}>Hide investigation</button>
                                    </div>
                                  </>
                                )}
                              </div>
                            ) : null}
                            {isDiffOpen ? (
                              <div className="subsection">
                                <p className="section-label">Diff quick view</p>
                                {!item.latest_diff_snapshot_id ? <p>No comparable diff.</p> : !diff ? <p>No comparable diff.</p> : <p>{diff.diff_summary}</p>}
                              </div>
                            ) : null}
                            {isRunContextOpen ? (
                              <div className="subsection">
                                <p className="section-label">Run context quick view</p>
                                {!item.correlated_run_id ? <p>No correlated run.</p> : (
                                  <ul className="key-value-list">
                                    <li><span>Run id</span><strong>{item.correlated_run_id}</strong></li>
                                    <li><span>Timestamp</span><strong>{formatDate(item.correlated_run_timestamp)}</strong></li>
                                    <li><span>Profile</span><strong>{item.correlated_profile_name ?? 'n/a'}</strong></li>
                                    <li><span>Fingerprint</span><strong>{detail?.correlated_profile_fingerprint ?? item.correlated_profile_fingerprint ?? 'n/a'}</strong></li>
                                  </ul>
                                )}
                              </div>
                            ) : null}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </SectionCard>

            <div className="content-grid content-grid--two-columns">
              <SectionCard eyebrow="Trace" title="Recent trace availability" description="Use trace explorer as the drill-down layer; cockpit does not duplicate it.">
                <ul className="key-value-list">
                  <li><span>Trace roots</span><strong>{snapshot.traceSummary?.total_roots ?? 0}</strong></li>
                  <li><span>Trace nodes</span><strong>{snapshot.traceSummary?.total_nodes ?? 0}</strong></li>
                  <li><span>Latest query</span><strong>{formatDate(snapshot.traceSummary?.latest_query_run?.created_at)}</strong></li>
                </ul>
                <div className="button-row">
                  <button className="secondary-button" type="button" onClick={() => navigate('/trace')}>Open trace explorer</button>
                </div>
              </SectionCard>

              <SectionCard eyebrow="Quick links" title="Specialized pages" description="Cockpit centralizes operations but keeps module pages as source of truth.">
                <div className="button-row">
                  {quickLinks.map((link) => (
                    <button key={link.path} className="ghost-button" type="button" onClick={() => navigate(link.path)}>{link.label}</button>
                  ))}
                </div>
                <p className="muted-text">Last cockpit refresh: {formatDate(snapshot.lastUpdatedAt)}.</p>
                {Object.keys(snapshot.failures).length > 0 ? <p className="warning-text">Partial data: {Object.entries(snapshot.failures).map(([key, value]) => `${key}: ${value}`).join(' | ')}</p> : null}
              </SectionCard>
            </div>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
