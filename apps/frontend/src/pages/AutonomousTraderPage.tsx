import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import {
  getAutonomousTraderCandidates,
  getAutonomousTraderDecisions,
  getAutonomousTraderExecutions,
  getAutonomousTraderOutcomes,
  getAutonomousTraderSummary,
  getAutonomousTraderWatchRecords,
  runAutonomousTraderCycle,
  runAutonomousTraderWatchCycle,
} from '../services/autonomousTrader';
import type {
  AutonomousTradeCandidate,
  AutonomousTradeDecision,
  AutonomousTradeExecution,
  AutonomousTradeOutcome,
  AutonomousTradeWatchRecord,
  AutonomousTraderSummary,
} from '../types/autonomousTrader';

export function AutonomousTraderPage() {
  const [summary, setSummary] = useState<AutonomousTraderSummary | null>(null);
  const [candidates, setCandidates] = useState<AutonomousTradeCandidate[]>([]);
  const [decisions, setDecisions] = useState<AutonomousTradeDecision[]>([]);
  const [executions, setExecutions] = useState<AutonomousTradeExecution[]>([]);
  const [watchRecords, setWatchRecords] = useState<AutonomousTradeWatchRecord[]>([]);
  const [outcomes, setOutcomes] = useState<AutonomousTradeOutcome[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, d, e, w, o] = await Promise.all([
        getAutonomousTraderSummary(),
        getAutonomousTraderCandidates(),
        getAutonomousTraderDecisions(),
        getAutonomousTraderExecutions(),
        getAutonomousTraderWatchRecords(),
        getAutonomousTraderOutcomes(),
      ]);
      setSummary(s); setCandidates(c); setDecisions(d); setExecutions(e); setWatchRecords(w); setOutcomes(o);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load autonomous trader.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  const runCycle = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousTraderCycle(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const runWatchCycle = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousTraderWatchCycle(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const cards = useMemo(() => [
    ['Candidates considered', summary?.considered_candidate_count ?? 0],
    ['Watchlist', summary?.watchlist_count ?? 0],
    ['Approved for paper execution', summary?.approved_for_execution_count ?? 0],
    ['Executed', summary?.executed_paper_trade_count ?? 0],
    ['Blocked', summary?.blocked_count ?? 0],
    ['Closed', summary?.closed_position_count ?? 0],
    ['Postmortem handoffs', summary?.postmortem_handoff_count ?? 0],
  ], [summary]);

  return <div className="page-stack">
    <PageHeader eyebrow="Autonomous paper loop" title="/autonomous-trader" description="Paper-only, governed autonomy with minimal human intervention. No real money, no live broker routing, and explicit risk/policy/runtime authority boundaries."
      actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void runCycle()}>{busy ? 'Running...' : 'Run autonomous trade cycle'}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runWatchCycle()}>Run watch cycle</button></div>} />

    <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined} loadingTitle="Loading autonomous trader" errorTitle="Could not load autonomous trader" loadingDescription="Collecting cycle summary, candidates, decisions, executions, watch records, and outcomes.">
      <SectionCard eyebrow="Summary" title="Cycle metrics" description="Autonomous paper trade-cycle run metrics with auditable counts.">
        <div className="dashboard-stat-grid">{cards.map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}</div>
      </SectionCard>
      <SectionCard eyebrow="Candidates" title="Consolidated intake" description="Candidates merged from opportunity/research/prediction/risk context."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Edge</th><th>Confidence</th><th>Status</th><th>Risk posture</th></tr></thead><tbody>{candidates.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.adjusted_edge}</td><td>{x.confidence}</td><td>{x.candidate_status}</td><td>{x.risk_posture}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Decisions" title="Autonomous decisioning" description="Transparent and explicit watch/execute/block decisions."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Decision</th><th>Rationale</th><th>Status</th></tr></thead><tbody>{decisions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.decision_type}</td><td>{x.rationale}</td><td>{x.decision_status}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Executions" title="Paper executions" description="Paper-only execution linkage with sizing summary and linked paper trade."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Execution status</th><th>Sizing summary</th><th>Paper trade</th></tr></thead><tbody>{executions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.execution_status}</td><td>{x.sizing_summary}</td><td>{x.linked_paper_trade ?? '-'}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Watch" title="Automated watch records" description="Post-entry watch logic for sentiment, market move, and risk change."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Watch status</th><th>Sentiment shift</th><th>Market move</th><th>Risk change</th></tr></thead><tbody>{watchRecords.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.watch_status}</td><td>{x.sentiment_shift_detected ? 'YES' : 'NO'}</td><td>{x.market_move_detected ? 'YES' : 'NO'}</td><td>{x.risk_change_detected ? 'YES' : 'NO'}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Outcomes" title="Cycle outcomes" description="Outcome tracking and conservative postmortem/learning handoffs."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Outcome type</th><th>Status</th><th>Postmortem</th><th>Learning</th></tr></thead><tbody>{outcomes.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.outcome_type}</td><td>{x.outcome_status}</td><td>{x.send_to_postmortem ? 'YES' : 'NO'}</td><td>{x.send_to_learning ? 'YES' : 'NO'}</td></tr>)}</tbody></table></div></SectionCard>
    </DataStateWrapper>
  </div>;
}
