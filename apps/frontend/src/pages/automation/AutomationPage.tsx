import { useCallback, useEffect, useMemo, useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusCard } from '../../components/StatusCard';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { useDemoFlowRefresh } from '../../hooks/useDemoFlowRefresh';
import { publishDemoFlowRefresh } from '../../lib/demoFlow';
import { getPolicySummary } from '../../services/policy';
import { navigate } from '../../lib/router';
import {
  getAutomationRuns,
  getAutomationSummary,
  runDemoCycle,
  runFullLearningCycle,
  runRebuildLearningMemory,
  runGenerateSignals,
  runGenerateTradeReviews,
  runRevaluePortfolio,
  runSimulationTick,
  runSyncDemoState,
} from '../../services/automation';
import type { DemoAutomationActionType, DemoAutomationRun, DemoAutomationStatus } from '../../types/automation';
import type { SystemStatus } from '../../types/system';

const actionDefinitions: Array<{
  actionType: DemoAutomationActionType;
  label: string;
  description: string;
  tone: 'primary' | 'secondary';
  run: () => Promise<DemoAutomationRun>;
}> = [
  {
    actionType: 'simulate_tick',
    label: 'Run simulation tick',
    description: 'Advance the local market demo by one explicit simulation step.',
    tone: 'secondary',
    run: () => runSimulationTick('automation_page'),
  },
  {
    actionType: 'generate_signals',
    label: 'Generate signals',
    description: 'Refresh mock-agent demo signals from the updated local market state.',
    tone: 'secondary',
    run: () => runGenerateSignals('automation_page'),
  },
  {
    actionType: 'revalue_portfolio',
    label: 'Revalue portfolio',
    description: 'Mark the paper portfolio to the latest local market prices and capture a snapshot.',
    tone: 'secondary',
    run: () => runRevaluePortfolio('automation_page'),
  },
  {
    actionType: 'generate_trade_reviews',
    label: 'Generate trade reviews',
    description: 'Create or refresh demo post-mortem reviews for executed paper trades.',
    tone: 'secondary',
    run: () => runGenerateTradeReviews('automation_page'),
  },
  {
    actionType: 'sync_demo_state',
    label: 'Refresh demo state',
    description: 'Collect a lightweight backend summary without executing trades or autonomous behavior.',
    tone: 'secondary',
    run: () => runSyncDemoState('automation_page'),
  },
  {
    actionType: 'run_demo_cycle',
    label: 'Run full demo cycle',
    description: 'Run simulation, signal generation, revalue, and review generation in safe sequence.',
    tone: 'primary',
    run: () => runDemoCycle('automation_page'),
  },
  {
    actionType: 'rebuild_learning_memory',
    label: 'Rebuild learning memory',
    description: 'Rebuild heuristic learning memory and conservative adjustments with full traceability.',
    tone: 'secondary',
    run: () => runRebuildLearningMemory('automation_page'),
  },
  {
    actionType: 'run_full_learning_cycle',
    label: 'Run full learning cycle',
    description: 'Run demo cycle plus controlled learning rebuild in one auditable operation.',
    tone: 'primary',
    run: () => runFullLearningCycle('automation_page'),
  },
];

const guidedFlow = [
  'Run simulation tick to move the local market state.',
  'Generate signals to surface demo opportunities from the refreshed market state.',
  'Open a market and inspect the signal plus risk context before any manual paper trade.',
  'Execute a paper trade manually from Market detail when you want to continue the demo flow.',
  'Revalue portfolio to update equity and capture the latest paper account snapshot.',
  'Generate trade reviews to close the loop in Post-Mortem.',
  'Rebuild learning memory to apply conservative adjustments in future proposal/risk cycles.',
];

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return 'Pending';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatActionLabel(value: string) {
  return value
    .split('_')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

function mapRunStatus(status: DemoAutomationStatus): 'online' | 'offline' | 'loading' | 'ready' | 'pending' | 'neutral' {
  if (status === 'SUCCESS') {
    return 'ready';
  }
  if (status === 'FAILED') {
    return 'offline';
  }
  if (status === 'PARTIAL') {
    return 'pending';
  }
  return 'loading';
}

export function AutomationPage() {
  const [runs, setRuns] = useState<DemoAutomationRun[]>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getAutomationSummary>> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<DemoAutomationActionType | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [latestActionRun, setLatestActionRun] = useState<DemoAutomationRun | null>(null);
  const [policySummary, setPolicySummary] = useState<Awaited<ReturnType<typeof getPolicySummary>> | null>(null);

  const loadAutomationState = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [runsResponse, summaryResponse, policySummaryResponse] = await Promise.all([getAutomationRuns(12), getAutomationSummary(), getPolicySummary()]);
      setRuns(runsResponse);
      setSummary(summaryResponse);
      setPolicySummary(policySummaryResponse);
      if (!latestActionRun && summaryResponse.latest_run) {
        setLatestActionRun(summaryResponse.latest_run);
      }
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load automation demo state from the backend.'));
    } finally {
      setIsLoading(false);
    }
  }, [latestActionRun]);

  useEffect(() => {
    void loadAutomationState();
  }, [loadAutomationState]);

  useDemoFlowRefresh(loadAutomationState);

  const handleAction = useCallback(
    async (actionType: DemoAutomationActionType, runner: () => Promise<DemoAutomationRun>) => {
      setActiveAction(actionType);
      setActionMessage(null);
      setActionError(null);

      try {
        const run = await runner();
        setLatestActionRun(run);
        setActionMessage(run.summary);
        await loadAutomationState();
        publishDemoFlowRefresh(`automation-${actionType}`);
      } catch (runError) {
        setActionError(getErrorMessage(runError, `Could not execute ${formatActionLabel(actionType)}.`));
      } finally {
        setActiveAction(null);
      }
    },
    [loadAutomationState],
  );

  const statusCards = useMemo(() => {
    if (!summary) {
      return [];
    }

    const keyActions: DemoAutomationActionType[] = [
      'simulate_tick',
      'generate_signals',
      'revalue_portfolio',
      'generate_trade_reviews',
    ];

    return keyActions.map((actionType) => {
      const run = summary.last_by_action[actionType] ?? null;
      const status: SystemStatus = run ? (run.status === 'FAILED' ? 'offline' : run.status === 'PARTIAL' ? 'degraded' : 'online') : 'loading';
      return {
        title: formatActionLabel(actionType),
        status,
        description: run
          ? `${run.summary} Triggered ${formatTimestamp(run.started_at)} from ${run.triggered_from.replace('_', ' ')}.`
          : 'No run recorded yet for this demo control.',
        details: run
          ? [
              { label: 'Started', value: formatTimestamp(run.started_at) },
              { label: 'Finished', value: formatTimestamp(run.finished_at) },
            ]
          : [],
      };
    });
  }, [summary]);

  return (
    <div className="page-stack automation-page">
      <PageHeader
        eyebrow="Demo control center"
        title="Automation"
        description="Guided local-first automation controls for the demo workflow. This page accelerates simulation, signals, portfolio revalue, and review generation without enabling auto-trading or autonomous agents."
        actions={
          <div className="button-row">
            <button type="button" className="secondary-button" onClick={() => navigate('/semi-auto')}>
              Open semi-auto
            </button>
            <button type="button" className="secondary-button" onClick={() => navigate('/learning')}>
              Open learning
            </button>
            <button type="button" className="secondary-button" onClick={() => navigate('/evaluation')}>
              Open evaluation
            </button>
          </div>
        }
      />

      <StatusCard
        title="Automation mode"
        status={activeAction ? 'loading' : 'online'}
        description={
          activeAction
            ? `Running ${formatActionLabel(activeAction)}. Buttons stay disabled until the backend returns a final result.`
            : 'All automation remains user-triggered, local-first, and demo-only. Nothing here executes trades automatically.'
        }
        details={[
          { label: 'Control model', value: 'Explicit user actions only' },
          { label: 'Trading mode', value: 'Manual paper trading only' },
          { label: 'Background jobs', value: 'Not enabled in this layer' },
        ]}
      />

      <DataStateWrapper
        isLoading={isLoading}
        isError={Boolean(error)}
        errorMessage={error ?? undefined}
        loadingTitle="Loading automation controls"
        loadingDescription="Fetching automation runs and summary data from the local backend."
      >
        <div className="content-grid content-grid--two-columns">
          <SectionCard
            eyebrow="Actions"
            title="Run demo controls"
            description="Each action is explicit, sequential, and safe for the current local demo environment."
          >
            <div className="automation-action-grid">
              {actionDefinitions.map((action) => {
                const isBusy = activeAction !== null;
                const isCurrent = activeAction === action.actionType;
                return (
                  <article key={action.actionType} className="automation-action-card">
                    <div className="automation-action-card__header">
                      <div>
                        <h3>{action.label}</h3>
                        <p>{action.description}</p>
                      </div>
                      <StatusBadge tone={isCurrent ? 'loading' : 'neutral'}>{isCurrent ? 'Running' : 'Manual'}</StatusBadge>
                    </div>
                    <button
                      type="button"
                      className={action.tone === 'primary' ? 'primary-button' : 'secondary-button'}
                      onClick={() => void handleAction(action.actionType, action.run)}
                      disabled={isBusy}
                    >
                      {isCurrent ? 'Running…' : action.label}
                    </button>
                  </article>
                );
              })}
            </div>

            {actionMessage ? <p className="automation-feedback automation-feedback--success">{actionMessage}</p> : null}
            {actionError ? <p className="automation-feedback automation-feedback--error">{actionError}</p> : null}
          </SectionCard>

          <SectionCard
            eyebrow="Guided flow"
            title="Recommended operator sequence"
            description="Use the controls below to accelerate the existing end-to-end demo without turning it into an autonomous system."
            aside={<StatusBadge tone="ready">Human in the loop</StatusBadge>}
          >
            <ol className="automation-flow-list">
              {guidedFlow.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <div className="automation-link-row">
              <button type="button" className="secondary-button" onClick={() => navigate('/markets')}>
                Open markets
              </button>
              <button type="button" className="secondary-button" onClick={() => navigate('/portfolio')}>
                Open portfolio
              </button>
              <button type="button" className="secondary-button" onClick={() => navigate('/postmortem')}>
                Open post-mortem
              </button>
            </div>
          </SectionCard>
        </div>

        <div className="content-grid content-grid--two-columns">
          <SectionCard
            eyebrow="Policy engine"
            title="Automation stays approval-aware"
            description="Automation controls prepare and refresh demo state, but they do not auto-trade. Future automated trade proposals should pass through the policy engine first."
          >
            <div className="automation-policy-card">
              <p>
                In this stage, automation only advances market simulation, signals, portfolio revalue, and post-mortem generation.
                Any future automated trade suggestion must still be evaluated by the policy engine before execution.
              </p>
              <dl className="automation-run-meta">
                <div>
                  <dt>Auto-approved</dt>
                  <dd>{policySummary?.auto_approve_count ?? '—'}</dd>
                </div>
                <div>
                  <dt>Manual approval</dt>
                  <dd>{policySummary?.approval_required_count ?? '—'}</dd>
                </div>
                <div>
                  <dt>Hard blocked</dt>
                  <dd>{policySummary?.hard_block_count ?? '—'}</dd>
                </div>
              </dl>
              <p className="muted-text">
                Current model: automation can prepare context, but execution remains human-triggered and policy-governed.
              </p>
            </div>
          </SectionCard>
        </div>

        {statusCards.length > 0 ? (
          <div className="content-grid content-grid--two-columns automation-summary-grid">
            {statusCards.map((card) => (
              <StatusCard key={card.title} title={card.title} status={card.status} description={card.description} details={card.details} />
            ))}
          </div>
        ) : null}

        <div className="content-grid content-grid--two-columns">
          <SectionCard
            eyebrow="Latest run"
            title="Last execution result"
            description="The most recent automation run stays visible here, including step-level status when applicable."
          >
            <DataStateWrapper
              isLoading={false}
              isError={false}
              isEmpty={!latestActionRun}
              emptyTitle="No automation runs yet"
              emptyDescription="Start with a simulation tick, refresh the demo state, or run the full demo cycle to create local automation history."
            >
              {latestActionRun ? (
                <div className="automation-latest-run">
                  <div className="automation-latest-run__header">
                    <div>
                      <h3>{formatActionLabel(latestActionRun.action_type)}</h3>
                      <p>{latestActionRun.summary}</p>
                    </div>
                    <StatusBadge tone={mapRunStatus(latestActionRun.status)}>{latestActionRun.status}</StatusBadge>
                  </div>
                  <dl className="automation-run-meta">
                    <div>
                      <dt>Started</dt>
                      <dd>{formatTimestamp(latestActionRun.started_at)}</dd>
                    </div>
                    <div>
                      <dt>Finished</dt>
                      <dd>{formatTimestamp(latestActionRun.finished_at)}</dd>
                    </div>
                    <div>
                      <dt>Triggered from</dt>
                      <dd>{latestActionRun.triggered_from.replace('_', ' ')}</dd>
                    </div>
                  </dl>
                  {latestActionRun.step_results.length > 0 ? (
                    <div className="automation-step-list">
                      {latestActionRun.step_results.map((step) => (
                        <article key={`${latestActionRun.id}-${step.step_name}`} className="automation-step-card">
                          <div className="automation-step-card__header">
                            <h4>{formatActionLabel(step.step_name)}</h4>
                            <StatusBadge tone={step.status === 'SUCCESS' ? 'ready' : step.status === 'FAILED' ? 'offline' : 'pending'}>
                              {step.status}
                            </StatusBadge>
                          </div>
                          <p>{step.summary}</p>
                        </article>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </DataStateWrapper>
          </SectionCard>

          <SectionCard
            eyebrow="Recent history"
            title="Automation runs"
            description="Recent action runs stay visible here so the demo remains traceable and easy to explain."
            aside={<StatusBadge tone="neutral">{runs.length} recent</StatusBadge>}
          >
            <DataStateWrapper
              isLoading={false}
              isError={false}
              isEmpty={runs.length === 0}
              emptyTitle="No automation runs yet"
              emptyDescription="No automation runs yet. Start with a simulation tick or run the full demo cycle."
            >
              <div className="markets-table-wrapper">
                <table className="markets-table markets-table--compact automation-runs-table">
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Status</th>
                      <th>Started</th>
                      <th>Finished</th>
                      <th>Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((run) => (
                      <tr key={run.id}>
                        <td>
                          <strong>{formatActionLabel(run.action_type)}</strong>
                        </td>
                        <td>
                          <StatusBadge tone={mapRunStatus(run.status)}>{run.status}</StatusBadge>
                        </td>
                        <td>{formatTimestamp(run.started_at)}</td>
                        <td>{formatTimestamp(run.finished_at)}</td>
                        <td>{run.summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DataStateWrapper>
          </SectionCard>
        </div>
      </DataStateWrapper>
    </div>
  );
}
