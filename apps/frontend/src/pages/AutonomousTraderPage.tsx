import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import {
  getAutonomousTraderCandidates,
  getAutonomousTraderDecisions,
  getAutonomousTraderExecutions,
  getAutonomousLearningHandoffs,
  getAutonomousFeedbackCandidateContexts,
  getAutonomousFeedbackInfluences,
  getAutonomousFeedbackRecommendations,
  getAutonomousFeedbackSummary,
  getAutonomousOutcomeHandoffRecommendations,
  getAutonomousOutcomeHandoffSummary,
  getAutonomousPostmortemHandoffs,
  getAutonomousTraderOutcomes,
  getAutonomousTraderSummary,
  getAutonomousTraderWatchRecords,
  runAutonomousOutcomeHandoff,
  runAutonomousTraderCycle,
  runAutonomousTraderWatchCycle,
  runAutonomousFeedbackReuse,
  runAutonomousSizing,
  getAutonomousSizingSummary,
  getAutonomousSizingContexts,
  getAutonomousSizingDecisions,
  getAutonomousSizingRecommendations,
  getAutonomousPositionWatchSummary,
  getAutonomousPositionWatchCandidates,
  getAutonomousPositionActionDecisions,
  getAutonomousPositionActionExecutions,
  getAutonomousPositionWatchRecommendations,
  runAutonomousPositionWatch,
  getAutonomousDispatchRecords,
  getAutonomousExecutionDecisions,
  getAutonomousExecutionIntakeCandidates,
  getAutonomousExecutionIntakeSummary,
  getAutonomousExecutionRecommendations,
  runAutonomousExecutionIntake,
} from '../services/autonomousTrader';
import type {
  AutonomousDispatchRecord,
  AutonomousExecutionDecision,
  AutonomousExecutionIntakeCandidate,
  AutonomousExecutionIntakeSummary,
  AutonomousExecutionRecommendation,
  AutonomousTradeCandidate,
  AutonomousTradeDecision,
  AutonomousTradeExecution,
  AutonomousTradeOutcome,
  AutonomousTradeWatchRecord,
  AutonomousTraderSummary,
  AutonomousOutcomeHandoffSummary,
  AutonomousPostmortemHandoff,
  AutonomousLearningHandoff,
  AutonomousOutcomeHandoffRecommendation,
  AutonomousFeedbackCandidateContext,
  AutonomousFeedbackInfluence,
  AutonomousFeedbackRecommendation,
  AutonomousFeedbackSummary,
  AutonomousSizingSummary,
  AutonomousSizingContext,
  AutonomousSizingDecision,
  AutonomousSizingRecommendation,
  AutonomousPositionWatchSummary,
  AutonomousPositionWatchCandidate,
  AutonomousPositionActionDecision,
  AutonomousPositionActionExecution,
  AutonomousPositionWatchRecommendation,
} from '../types/autonomousTrader';

export function AutonomousTraderPage() {
  const [summary, setSummary] = useState<AutonomousTraderSummary | null>(null);
  const [candidates, setCandidates] = useState<AutonomousTradeCandidate[]>([]);
  const [decisions, setDecisions] = useState<AutonomousTradeDecision[]>([]);
  const [executions, setExecutions] = useState<AutonomousTradeExecution[]>([]);
  const [watchRecords, setWatchRecords] = useState<AutonomousTradeWatchRecord[]>([]);
  const [outcomes, setOutcomes] = useState<AutonomousTradeOutcome[]>([]);
  const [handoffSummary, setHandoffSummary] = useState<AutonomousOutcomeHandoffSummary | null>(null);
  const [postmortemHandoffs, setPostmortemHandoffs] = useState<AutonomousPostmortemHandoff[]>([]);
  const [learningHandoffs, setLearningHandoffs] = useState<AutonomousLearningHandoff[]>([]);
  const [handoffRecommendations, setHandoffRecommendations] = useState<AutonomousOutcomeHandoffRecommendation[]>([]);
  const [feedbackSummary, setFeedbackSummary] = useState<AutonomousFeedbackSummary | null>(null);
  const [feedbackContexts, setFeedbackContexts] = useState<AutonomousFeedbackCandidateContext[]>([]);
  const [feedbackInfluences, setFeedbackInfluences] = useState<AutonomousFeedbackInfluence[]>([]);
  const [feedbackRecommendations, setFeedbackRecommendations] = useState<AutonomousFeedbackRecommendation[]>([]);

  const [sizingSummary, setSizingSummary] = useState<AutonomousSizingSummary | null>(null);
  const [sizingContexts, setSizingContexts] = useState<AutonomousSizingContext[]>([]);
  const [sizingDecisions, setSizingDecisions] = useState<AutonomousSizingDecision[]>([]);
  const [sizingRecommendations, setSizingRecommendations] = useState<AutonomousSizingRecommendation[]>([]);
  const [positionWatchSummary, setPositionWatchSummary] = useState<AutonomousPositionWatchSummary | null>(null);
  const [positionWatchCandidates, setPositionWatchCandidates] = useState<AutonomousPositionWatchCandidate[]>([]);
  const [positionActionDecisions, setPositionActionDecisions] = useState<AutonomousPositionActionDecision[]>([]);
  const [positionActionExecutions, setPositionActionExecutions] = useState<AutonomousPositionActionExecution[]>([]);
  const [positionWatchRecommendations, setPositionWatchRecommendations] = useState<AutonomousPositionWatchRecommendation[]>([]);
  const [executionIntakeSummary, setExecutionIntakeSummary] = useState<AutonomousExecutionIntakeSummary | null>(null);
  const [executionIntakeCandidates, setExecutionIntakeCandidates] = useState<AutonomousExecutionIntakeCandidate[]>([]);
  const [executionDecisions, setExecutionDecisions] = useState<AutonomousExecutionDecision[]>([]);
  const [dispatchRecords, setDispatchRecords] = useState<AutonomousDispatchRecord[]>([]);
  const [executionRecommendations, setExecutionRecommendations] = useState<AutonomousExecutionRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, c, d, e, w, o, hs, ph, lh, recs, fs, fc, fi, fr, ss, sc, sd, sr, pws, pwc, pad, pae, pwr, eis, eic, eds, drs, ers] = await Promise.all([
        getAutonomousTraderSummary(),
        getAutonomousTraderCandidates(),
        getAutonomousTraderDecisions(),
        getAutonomousTraderExecutions(),
        getAutonomousTraderWatchRecords(),
        getAutonomousTraderOutcomes(),
        getAutonomousOutcomeHandoffSummary(),
        getAutonomousPostmortemHandoffs(),
        getAutonomousLearningHandoffs(),
        getAutonomousOutcomeHandoffRecommendations(),
        getAutonomousFeedbackSummary(),
        getAutonomousFeedbackCandidateContexts(),
        getAutonomousFeedbackInfluences(),
        getAutonomousFeedbackRecommendations(),
        getAutonomousSizingSummary(),
        getAutonomousSizingContexts(),
        getAutonomousSizingDecisions(),
        getAutonomousSizingRecommendations(),
        getAutonomousPositionWatchSummary(),
        getAutonomousPositionWatchCandidates(),
        getAutonomousPositionActionDecisions(),
        getAutonomousPositionActionExecutions(),
        getAutonomousPositionWatchRecommendations(),
        getAutonomousExecutionIntakeSummary(),
        getAutonomousExecutionIntakeCandidates(),
        getAutonomousExecutionDecisions(),
        getAutonomousDispatchRecords(),
        getAutonomousExecutionRecommendations(),
      ]);
      setSummary(s); setCandidates(c); setDecisions(d); setExecutions(e); setWatchRecords(w); setOutcomes(o);
      setHandoffSummary(hs); setPostmortemHandoffs(ph); setLearningHandoffs(lh); setHandoffRecommendations(recs);
      setFeedbackSummary(fs); setFeedbackContexts(fc); setFeedbackInfluences(fi); setFeedbackRecommendations(fr);
      setSizingSummary(ss); setSizingContexts(sc); setSizingDecisions(sd); setSizingRecommendations(sr);
      setPositionWatchSummary(pws); setPositionWatchCandidates(pwc); setPositionActionDecisions(pad); setPositionActionExecutions(pae); setPositionWatchRecommendations(pwr);
      setExecutionIntakeSummary(eis); setExecutionIntakeCandidates(eic); setExecutionDecisions(eds); setDispatchRecords(drs); setExecutionRecommendations(ers);
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

  const runOutcomeHandoff = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousOutcomeHandoff(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const runFeedbackReuse = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousFeedbackReuse(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const runSizing = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousSizing(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const runPositionWatch = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousPositionWatch(); await loadData(); } finally { setBusy(false); }
  }, [loadData]);

  const runExecutionIntake = useCallback(async () => {
    setBusy(true);
    try { await runAutonomousExecutionIntake(); await loadData(); } finally { setBusy(false); }
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
      actions={<div className="button-row"><button type="button" className="primary-button" disabled={busy} onClick={() => void runCycle()}>{busy ? 'Running...' : 'Run autonomous trade cycle'}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runExecutionIntake()}>Run execution intake</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runWatchCycle()}>Run watch cycle</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runOutcomeHandoff()}>Run outcome handoff</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runFeedbackReuse()}>Run feedback reuse</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runSizing()}>Run sizing</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void runPositionWatch()}>Run position watch</button></div>} />

    <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined} loadingTitle="Loading autonomous trader" errorTitle="Could not load autonomous trader" loadingDescription="Collecting cycle summary, candidates, decisions, executions, watch records, and outcomes.">
      <SectionCard eyebrow="Summary" title="Cycle metrics" description="Autonomous paper trade-cycle run metrics with auditable counts.">
        <div className="dashboard-stat-grid">{cards.map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}</div>
      </SectionCard>
      <SectionCard eyebrow="Execution Readiness Intake" title="Risk → autonomous execution bridge" description="Paper-only, readiness-driven and dispatch-safe bridge. No live execution and no real money.">
        <div className="dashboard-stat-grid">{[
          ['Readiness considered', executionIntakeSummary?.considered_readiness_count ?? 0],
          ['Execute now', executionIntakeSummary?.execute_now_count ?? 0],
          ['Execute reduced', executionIntakeSummary?.execute_reduced_count ?? 0],
          ['Watch', executionIntakeSummary?.watch_count ?? 0],
          ['Defer', executionIntakeSummary?.defer_count ?? 0],
          ['Blocked', executionIntakeSummary?.blocked_count ?? 0],
          ['Dispatched', executionIntakeSummary?.dispatch_count ?? 0],
        ].map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}</div>
      </SectionCard>
      <SectionCard eyebrow="Execution intake candidates" title="Readiness intake candidates" description="Candidate-level readiness context consumed from risk outputs."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Readiness confidence</th><th>Approval</th><th>Sizing method</th><th>Status</th><th>Summary</th></tr></thead><tbody>{executionIntakeCandidates.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.readiness_confidence}</td><td>{x.approval_status || '-'}</td><td>{x.sizing_method || '-'}</td><td>{x.intake_status}</td><td>{x.execution_context_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Execution decisions" title="Governed execution decisions" description="Explicit execute/reduced/watch/defer/block/manual-review decisions."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Decision type</th><th>Status</th><th>Confidence</th><th>Rationale</th></tr></thead><tbody>{executionDecisions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.decision_type}</td><td>{x.decision_status}</td><td>{x.decision_confidence}</td><td>{x.rationale}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Dispatch records" title="Paper dispatch records" description="Dispatch status and mode for readiness-driven paper execution only."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Status</th><th>Mode</th><th>Quantity</th><th>Notional</th><th>Summary</th></tr></thead><tbody>{dispatchRecords.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.dispatch_status}</td><td>{x.dispatch_mode}</td><td>{x.dispatched_quantity ?? '-'}</td><td>{x.dispatched_notional ?? '-'}</td><td>{x.dispatch_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Execution recommendations" title="Conservative execution recommendations" description="Audit-friendly recommendation outputs for dispatch or non-dispatch paths."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{executionRecommendations.map((x) => <tr key={x.id}><td>{x.recommendation_type}</td><td>{x.rationale}</td><td>{x.blockers?.join(', ') || '-'}</td><td>{x.confidence}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Candidates" title="Consolidated intake" description="Candidates merged from opportunity/research/prediction/risk context."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Edge</th><th>Confidence</th><th>Status</th><th>Risk posture</th></tr></thead><tbody>{candidates.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.adjusted_edge}</td><td>{x.confidence}</td><td>{x.candidate_status}</td><td>{x.risk_posture}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Decisions" title="Autonomous decisioning" description="Transparent and explicit watch/execute/block decisions."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Decision</th><th>Rationale</th><th>Status</th></tr></thead><tbody>{decisions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.decision_type}</td><td>{x.rationale}</td><td>{x.decision_status}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Executions" title="Paper executions" description="Paper-only execution linkage with sizing summary and linked paper trade."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Execution status</th><th>Sizing summary</th><th>Paper trade</th></tr></thead><tbody>{executions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.execution_status}</td><td>{x.sizing_summary}</td><td>{x.linked_paper_trade ?? '-'}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Watch" title="Automated watch records" description="Post-entry watch logic for sentiment, market move, and risk change."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Watch status</th><th>Sentiment shift</th><th>Market move</th><th>Risk change</th></tr></thead><tbody>{watchRecords.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.watch_status}</td><td>{x.sentiment_shift_detected ? 'YES' : 'NO'}</td><td>{x.market_move_detected ? 'YES' : 'NO'}</td><td>{x.risk_change_detected ? 'YES' : 'NO'}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Open Position Management" title="Post-entry autonomous watch" description="Paper-only, sentiment-aware, risk-first management of already-open paper positions. No live execution and no real money.">
        <div className="dashboard-stat-grid">{[
          ['Positions considered', positionWatchSummary?.considered_position_count ?? 0],
          ['Hold', positionWatchSummary?.hold_count ?? 0],
          ['Reduce', positionWatchSummary?.reduce_count ?? 0],
          ['Close', positionWatchSummary?.close_count ?? 0],
          ['Review required', positionWatchSummary?.review_required_count ?? 0],
          ['Executed reduce/close', (positionWatchSummary?.executed_reduce_count ?? 0) + (positionWatchSummary?.executed_close_count ?? 0)],
        ].map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}</div>
      </SectionCard>
      <SectionCard eyebrow="Watch candidates" title="Open positions under active monitoring" description="Entry-vs-current drift, sentiment state, risk state, and portfolio pressure state."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Entry/current prob</th><th>Entry/current edge</th><th>Sentiment</th><th>Risk</th><th>Portfolio</th><th>Status</th></tr></thead><tbody>{positionWatchCandidates.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.entry_probability ?? '-'} → {x.current_probability ?? '-'}</td><td>{x.entry_edge ?? '-'} → {x.current_edge ?? '-'}</td><td>{x.sentiment_state}</td><td>{x.risk_state}</td><td>{x.portfolio_pressure_state}</td><td>{x.candidate_status}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Action decisions" title="Hold/reduce/close/review decisions" description="Explicit post-entry decision records with confidence and rationale."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Type</th><th>Status</th><th>Confidence</th><th>Reduction</th><th>Rationale</th></tr></thead><tbody>{positionActionDecisions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.decision_type}</td><td>{x.decision_status}</td><td>{x.decision_confidence}</td><td>{x.reduction_fraction ?? '-'}</td><td>{x.rationale}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Action executions" title="Reduce/close paper execution" description="Governed and auditable paper-only execution path for actioned decisions."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Type</th><th>Status</th><th>Qty before/after</th><th>Notional before/after</th><th>Summary</th></tr></thead><tbody>{positionActionExecutions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.execution_type}</td><td>{x.execution_status}</td><td>{x.quantity_before ?? '-'} → {x.quantity_after ?? '-'}</td><td>{x.notional_before ?? '-'} → {x.notional_after ?? '-'}</td><td>{x.summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Recommendations" title="Conservative open-position recommendations" description="Recommendation lineage for hold/reduce/close/review outputs."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{positionWatchRecommendations.map((x) => <tr key={x.id}><td>{x.recommendation_type}</td><td>{x.rationale}</td><td>{x.blockers?.join(', ') || '-'}</td><td>{x.confidence}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Outcomes" title="Cycle outcomes" description="Outcome tracking and conservative postmortem/learning handoffs."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Outcome type</th><th>Status</th><th>Postmortem</th><th>Learning</th></tr></thead><tbody>{outcomes.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.outcome_type}</td><td>{x.outcome_status}</td><td>{x.send_to_postmortem ? 'YES' : 'NO'}</td><td>{x.send_to_learning ? 'YES' : 'NO'}</td></tr>)}</tbody></table></div></SectionCard>


      <SectionCard eyebrow="Risk & Kelly Sizing" title="Autonomous paper sizing bridge" description="Paper-only bounded Kelly sizing that remains risk-first and portfolio-aware. No live execution and no real money.">
        <div className="dashboard-stat-grid">{[
          ['Candidates considered', sizingSummary?.considered_candidate_count ?? 0],
          ['Approved for sizing', sizingSummary?.approved_for_sizing_count ?? 0],
          ['Reduced by risk', sizingSummary?.reduced_by_risk_count ?? 0],
          ['Reduced by portfolio', sizingSummary?.reduced_by_portfolio_count ?? 0],
          ['Blocked', sizingSummary?.blocked_for_sizing_count ?? 0],
          ['Sized for execution', sizingSummary?.sized_for_execution_count ?? 0],
        ].map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}</div>
      </SectionCard>
      <SectionCard eyebrow="Sizing contexts" title="Context inputs" description="Traceable prediction/risk/portfolio/feedback context before sizing."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Edge</th><th>Confidence</th><th>Uncertainty</th><th>Risk posture</th><th>Portfolio posture</th><th>Status</th></tr></thead><tbody>{sizingContexts.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.adjusted_edge}</td><td>{x.confidence}</td><td>{x.uncertainty ?? '-'}</td><td>{x.risk_posture}</td><td>{x.portfolio_posture}</td><td>{x.context_status}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Sizing decisions" title="Bounded Kelly decisions" description="Pre-adjustment to final paper quantity with conservative caps and discounts."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Method</th><th>Status</th><th>Kelly base</th><th>Applied fraction</th><th>Notional before/after</th><th>Final qty</th><th>Summary</th></tr></thead><tbody>{sizingDecisions.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.sizing_method}</td><td>{x.decision_status}</td><td>{x.base_kelly_fraction ?? '-'}</td><td>{x.applied_fraction ?? '-'}</td><td>{x.notional_before_adjustment ?? '-'} → {x.notional_after_adjustment ?? '-'}</td><td>{x.final_paper_quantity ?? '-'}</td><td>{x.decision_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Sizing recommendations" title="Conservative guidance" description="Explicit recommendation records for blocks, caps, and fallback modes."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{sizingRecommendations.map((x) => <tr key={x.id}><td>{x.recommendation_type}</td><td>{x.rationale}</td><td>{x.blockers?.join(', ') || '-'}</td><td>{x.confidence}</td></tr>)}</tbody></table></div></SectionCard>

      <SectionCard eyebrow="Outcome Handoffs" title="Autonomous post-trade closure" description="Governed paper-only handoff engine from outcome → postmortem → learning. No real money and no live routing.">
        <div className="dashboard-stat-grid">
          {[
            ['Outcomes considered', handoffSummary?.considered_outcome_count ?? 0],
            ['Postmortem eligible', handoffSummary?.eligible_postmortem_count ?? 0],
            ['Learning eligible', handoffSummary?.eligible_learning_count ?? 0],
            ['Emitted', handoffSummary?.emitted_count ?? 0],
            ['Duplicate skipped', handoffSummary?.duplicate_skipped_count ?? 0],
            ['Blocked', handoffSummary?.blocked_count ?? 0],
          ].map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}
        </div>
      </SectionCard>
      <SectionCard eyebrow="Postmortem handoffs" title="Postmortem activation bridge" description="Explicit lineage from autonomous outcomes into postmortem board runs."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Outcome</th><th>Trigger</th><th>Status</th><th>Postmortem run</th><th>Summary</th></tr></thead><tbody>{postmortemHandoffs.map((x) => <tr key={x.id}><td>{x.linked_outcome}</td><td>{x.trigger_reason}</td><td>{x.handoff_status}</td><td>{x.linked_postmortem_run ?? '-'}</td><td>{x.handoff_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Learning handoffs" title="Learning capture bridge" description="Conservative capture for later governed reuse; no auto-retune or auto-promote."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Outcome</th><th>Trigger</th><th>Status</th><th>Learning run</th><th>Summary</th></tr></thead><tbody>{learningHandoffs.map((x) => <tr key={x.id}><td>{x.linked_outcome}</td><td>{x.trigger_reason}</td><td>{x.handoff_status}</td><td>{x.linked_learning_run ?? '-'}</td><td>{x.handoff_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Recommendations" title="Conservative handoff guidance" description="Transparent recommendation records for every outcome-handoff decision."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{handoffRecommendations.map((x) => <tr key={x.id}><td>{x.recommendation_type}</td><td>{x.rationale}</td><td>{x.blockers?.join(', ') || '-'}</td><td>{x.confidence}</td></tr>)}</tbody></table></div></SectionCard>

      <SectionCard eyebrow="Learning & Feedback Reuse" title="Next-cycle conservative memory bridge" description="Reuses postmortem and learning precedents for the next paper cycle with bounded influence only. No auto-retune and no model switching.">
        <div className="dashboard-stat-grid">
          {[
            ['Candidates considered', feedbackSummary?.considered_candidate_count ?? 0],
            ['Retrieval hits', feedbackSummary?.retrieval_hit_count ?? 0],
            ['Influence applied', feedbackSummary?.influence_applied_count ?? 0],
            ['Caution boosts', feedbackSummary?.watch_caution_count ?? 0],
            ['Blocked/reduced', feedbackSummary?.blocked_or_reduced_count ?? 0],
            ['No relevant learning', feedbackSummary?.no_relevant_learning_found_count ?? 0],
          ].map(([label, value]) => <article key={label} className="dashboard-stat-card"><span>{label}</span><strong>{value}</strong></article>)}
        </div>
      </SectionCard>
      <SectionCard eyebrow="Feedback contexts" title="Candidate memory context" description="Retrieved precedents and lessons before autonomous decisioning."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Status</th><th>Top precedents</th><th>Summary</th></tr></thead><tbody>{feedbackContexts.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.retrieval_status}</td><td>{x.top_precedent_count}</td><td>{x.context_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Feedback influence" title="Bounded influence records" description="Auditable confidence/caution/block actions derived from memory context."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Market</th><th>Type</th><th>Status</th><th>Reason codes</th><th>Confidence</th><th>Summary</th></tr></thead><tbody>{feedbackInfluences.map((x) => <tr key={x.id}><td>{x.market_title}</td><td>{x.influence_type}</td><td>{x.influence_status}</td><td>{x.influence_reason_codes?.join(', ') || '-'}</td><td>{x.pre_adjust_confidence ?? '-'} → {x.post_adjust_confidence ?? '-'}</td><td>{x.influence_summary}</td></tr>)}</tbody></table></div></SectionCard>
      <SectionCard eyebrow="Feedback recommendations" title="Conservative reuse recommendations" description="Explicit recommendations for caution, watch handling, and repeat-pattern blocking."><div className="markets-table-wrapper"><table className="markets-table"><thead><tr><th>Type</th><th>Rationale</th><th>Blockers</th><th>Confidence</th></tr></thead><tbody>{feedbackRecommendations.map((x) => <tr key={x.id}><td>{x.recommendation_type}</td><td>{x.rationale}</td><td>{x.blockers?.join(', ') || '-'}</td><td>{x.confidence}</td></tr>)}</tbody></table></div></SectionCard>
    </DataStateWrapper>
  </div>;
}
