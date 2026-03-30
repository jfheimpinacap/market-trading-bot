import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../components/EmptyState';
import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { navigate } from '../lib/router';
import {
  getFailurePatterns,
  getLearningAdjustments,
  getLearningApplicationRecords,
  getLearningRecommendations,
  getPostmortemLearningSummary,
  runPostmortemLearningLoop,
} from '../services/learningLoop';
import type {
  FailurePattern,
  LearningAdjustment,
  LearningApplicationRecord,
  LearningLoopSummary,
  LearningRecommendation,
} from '../types/learning';

function formatDate(value: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function toneForStatus(status: string) {
  if (['ACTIVE', 'SUCCESS'].includes(status)) return 'ready';
  if (['WATCH', 'PROPOSED', 'NEEDS_REVIEW'].includes(status)) return 'pending';
  return 'neutral';
}

export function LearningPage() {
  const [summary, setSummary] = useState<LearningLoopSummary | null>(null);
  const [patterns, setPatterns] = useState<FailurePattern[]>([]);
  const [adjustments, setAdjustments] = useState<LearningAdjustment[]>([]);
  const [applications, setApplications] = useState<LearningApplicationRecord[]>([]);
  const [recommendations, setRecommendations] = useState<LearningRecommendation[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [scopeFilter, setScopeFilter] = useState<string>('ALL');
  const [patternTypeFilter, setPatternTypeFilter] = useState<string>('ALL');
  const [adjustmentTypeFilter, setAdjustmentTypeFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryRes, patternsRes, adjustmentsRes, applicationsRes, recommendationsRes] = await Promise.all([
        getPostmortemLearningSummary(),
        getFailurePatterns(),
        getLearningAdjustments(),
        getLearningApplicationRecords(),
        getLearningRecommendations(),
      ]);
      setSummary(summaryRes);
      setPatterns(patternsRes);
      setAdjustments(adjustmentsRes);
      setApplications(applicationsRes);
      setRecommendations(recommendationsRes);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load postmortem learning loop data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleRunLoop = async () => {
    setIsRunning(true);
    try {
      await runPostmortemLearningLoop();
      await loadData();
    } finally {
      setIsRunning(false);
    }
  };

  const filteredPatterns = useMemo(() => patterns.filter((item) => (
    (statusFilter === 'ALL' || item.status === statusFilter)
    && (scopeFilter === 'ALL' || item.scope === scopeFilter)
    && (patternTypeFilter === 'ALL' || item.pattern_type === patternTypeFilter)
  )), [patterns, statusFilter, scopeFilter, patternTypeFilter]);

  const filteredAdjustments = useMemo(() => adjustments.filter((item) => (
    (statusFilter === 'ALL' || item.status === statusFilter)
    && (scopeFilter === 'ALL' || item.scope === scopeFilter)
    && (adjustmentTypeFilter === 'ALL' || item.adjustment_type === adjustmentTypeFilter)
  )), [adjustments, statusFilter, scopeFilter, adjustmentTypeFilter]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Postmortem learning loop"
        title="Learning"
        description="Structured loss analysis to failure patterns, conservative adjustments, and next-decision feedback. Local-first, paper-only, recommendation-first, and manual-first (no opaque auto-learning)."
        actions={(
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button type="button" className="secondary-button" onClick={() => navigate('/postmortem-board')}>Open Postmortem Board</button>
            <button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Open Cockpit</button>
            <button type="button" className="secondary-button" disabled={isRunning} onClick={() => void handleRunLoop()}>
              {isRunning ? 'Running postmortem learning loop...' : 'Run postmortem learning loop'}
            </button>
          </div>
        )}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!summary ? (
          <EmptyState eyebrow="No learning loop" title="No postmortem learning loop data yet" description="Run postmortem learning loop to derive reusable conservative adjustments." />
        ) : (
          <>
            <SectionCard eyebrow="Summary" title="Postmortem loop summary" description="Operational and auditable state of active/expired learning and downstream impact.">
              <div className="system-metadata-grid">
                <div><strong>Postmortem runs processed:</strong> {summary.runs_processed}</div>
                <div><strong>Active patterns:</strong> {summary.active_patterns}</div>
                <div><strong>Active adjustments:</strong> {summary.active_adjustments}</div>
                <div><strong>Expired adjustments:</strong> {summary.expired_adjustments}</div>
                <div><strong>Applications recorded:</strong> {summary.applications_recorded}</div>
                <div><strong>Manual review required:</strong> {summary.manual_review_required ? 'Yes' : 'No'}</div>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Filters" title="Filter learning artifacts" description="Filter by status/scope/pattern type/adjustment type.">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '0.75rem' }}>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="ALL">All status</option>
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="WATCH">WATCH</option>
                  <option value="EXPIRED">EXPIRED</option>
                  <option value="PROPOSED">PROPOSED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
                <select value={scopeFilter} onChange={(event) => setScopeFilter(event.target.value)}>
                  <option value="ALL">All scope</option>
                  <option value="global">global</option>
                  <option value="provider">provider</option>
                  <option value="category">category</option>
                  <option value="source_type">source_type</option>
                  <option value="signal_type">signal_type</option>
                  <option value="market">market</option>
                </select>
                <input value={patternTypeFilter} onChange={(event) => setPatternTypeFilter(event.target.value || 'ALL')} placeholder="pattern_type or ALL" />
                <input value={adjustmentTypeFilter} onChange={(event) => setAdjustmentTypeFilter(event.target.value || 'ALL')} placeholder="adjustment_type or ALL" />
              </div>
            </SectionCard>

            <SectionCard eyebrow="Failure patterns" title="Loss pattern registry" description="Explicit failure patterns extracted from postmortem board conclusions.">
              {filteredPatterns.length === 0 ? (
                <EmptyState
                  eyebrow="No patterns"
                  title="No postmortem learning patterns are available yet"
                  description="Run the learning loop to derive reusable adjustments. WATCH and EXPIRED are valid states."
                />
              ) : (
                <div className="table-wrapper"><table className="data-table"><thead><tr><th>Label</th><th>Pattern type</th><th>Scope</th><th>Severity</th><th>Recurrence</th><th>Status</th><th>Rationale</th></tr></thead><tbody>
                  {filteredPatterns.map((item) => (<tr key={item.id}><td>{item.canonical_label}</td><td>{item.pattern_type}</td><td>{item.scope}:{item.scope_key}</td><td>{item.severity_score}</td><td>{item.recurrence_count}</td><td><StatusBadge tone={toneForStatus(item.status)}>{item.status}</StatusBadge></td><td>{item.rationale}</td></tr>))}
                </tbody></table></div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Adjustments" title="Conservative learning adjustments" description="Bounded and traceable adjustments derived from failure patterns.">
              {filteredAdjustments.length === 0 ? <EmptyState eyebrow="No adjustments" title="No learning adjustments yet" description="Run the postmortem learning loop to derive adjustments." /> : (
                <div className="table-wrapper"><table className="data-table"><thead><tr><th>Type</th><th>Scope</th><th>Strength</th><th>Status</th><th>Expiration</th><th>Rationale</th><th>Postmortem</th></tr></thead><tbody>
                  {filteredAdjustments.map((item) => (<tr key={item.id}><td>{item.adjustment_type}</td><td>{item.scope}:{item.scope_key}</td><td>{item.adjustment_strength}</td><td><StatusBadge tone={toneForStatus(item.status)}>{item.status}</StatusBadge></td><td>{formatDate(item.expiration_hint)}</td><td>{item.rationale}</td><td>{item.linked_postmortem ?? '—'}</td></tr>))}
                </tbody></table></div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Application records" title="Downstream influence records" description="Where learning adjustments affected prediction/risk/proposal/signal_fusion.">
              {applications.length === 0 ? <EmptyState eyebrow="No applications" title="No application records yet" description="Application records appear after the learning loop and downstream components apply caution." /> : (
                <div className="table-wrapper"><table className="data-table"><thead><tr><th>Target</th><th>Type</th><th>Before</th><th>After</th><th>Adjustment</th><th>Rationale</th></tr></thead><tbody>
                  {applications.slice(0, 100).map((item) => (<tr key={item.id}><td>{item.target_component}</td><td>{item.application_type}</td><td>{item.before_value || '—'}</td><td>{item.after_value || '—'}</td><td>{item.linked_adjustment}</td><td>{item.rationale}</td></tr>))}
                </tbody></table></div>
              )}
            </SectionCard>

            <SectionCard eyebrow="Recommendations" title="Learning recommendations" description="Recommendation-first outputs for manual activation/watch/expiry/review actions.">
              {recommendations.length === 0 ? <EmptyState eyebrow="No recommendations" title="No recommendations yet" description="Run the learning loop to derive explicit recommendations." /> : (
                <div className="table-wrapper"><table className="data-table"><thead><tr><th>Recommendation</th><th>Rationale</th><th>Reason codes</th><th>Confidence</th><th>Blockers</th></tr></thead><tbody>
                  {recommendations.slice(0, 80).map((item) => (<tr key={item.id}><td><StatusBadge tone={toneForStatus(item.recommendation_type.includes('REQUIRE') ? 'NEEDS_REVIEW' : 'ACTIVE')}>{item.recommendation_type}</StatusBadge></td><td>{item.rationale}</td><td>{item.reason_codes.join(', ') || '—'}</td><td>{item.confidence}</td><td>{item.blockers.join(', ') || '—'}</td></tr>))}
                </tbody></table></div>
              )}
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
