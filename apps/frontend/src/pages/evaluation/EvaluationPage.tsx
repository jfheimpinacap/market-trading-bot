import { useCallback, useEffect, useMemo, useState } from 'react';
import { EmptyState } from '../../components/EmptyState';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { navigate } from '../../lib/router';
import {
  getCalibrationBuckets,
  getEffectivenessMetrics,
  getEvaluationRecommendations,
  getEvaluationRuntimeSummary,
  getOutcomeAlignmentRecords,
  runRuntimeEvaluation,
  type CalibrationBucket,
  type EffectivenessMetric,
  type EvaluationRecommendation,
  type EvaluationRuntimeSummary,
  type OutcomeAlignmentRecord,
} from '../../services/evaluationRuntime';

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function toPercent(value: string | number | null | undefined) {
  const numeric = value == null ? 0 : typeof value === 'number' ? value : Number(value);
  return `${(numeric * 100).toFixed(2)}%`;
}

const alignmentTone: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  WELL_CALIBRATED: 'ready',
  OVERCONFIDENT: 'offline',
  UNDERCONFIDENT: 'pending',
  GOOD_SKIP: 'ready',
  BAD_SKIP: 'offline',
  NO_EDGE_REALIZED: 'pending',
  NEEDS_REVIEW: 'neutral',
};

const metricTone: Record<string, 'ready' | 'pending' | 'offline' | 'neutral'> = {
  OK: 'ready',
  CAUTION: 'pending',
  POOR: 'offline',
  NEEDS_MORE_DATA: 'neutral',
};

export function EvaluationPage() {
  const [summary, setSummary] = useState<EvaluationRuntimeSummary | null>(null);
  const [alignment, setAlignment] = useState<OutcomeAlignmentRecord[]>([]);
  const [buckets, setBuckets] = useState<CalibrationBucket[]>([]);
  const [metrics, setMetrics] = useState<EffectivenessMetric[]>([]);
  const [recommendations, setRecommendations] = useState<EvaluationRecommendation[]>([]);
  const [providerFilter, setProviderFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [modelModeFilter, setModelModeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (providerFilter) params.provider = providerFilter;
      if (categoryFilter) params.category = categoryFilter;
      if (modelModeFilter) params.model_mode = modelModeFilter;
      if (statusFilter) params.status = statusFilter;

      const [summaryResponse, alignmentResponse, bucketsResponse, metricsResponse, recResponse] = await Promise.all([
        getEvaluationRuntimeSummary(),
        getOutcomeAlignmentRecords(params),
        getCalibrationBuckets(),
        getEffectivenessMetrics(),
        getEvaluationRecommendations(),
      ]);
      setSummary(summaryResponse);
      setAlignment(alignmentResponse);
      setBuckets(bucketsResponse);
      setMetrics(metricsResponse);
      setRecommendations(recResponse);
    } catch (loadError) {
      setError(getErrorMessage(loadError, 'Could not load quantitative evaluation data.'));
    } finally {
      setIsLoading(false);
    }
  }, [providerFilter, categoryFilter, modelModeFilter, statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const onRunRuntimeEvaluation = useCallback(async () => {
    setIsRunning(true);
    try {
      await runRuntimeEvaluation();
      await loadData();
    } catch (runError) {
      setError(getErrorMessage(runError, 'Runtime evaluation failed.'));
    } finally {
      setIsRunning(false);
    }
  }, [loadData]);

  const poorMetrics = useMemo(() => metrics.filter((item) => item.status === 'POOR').length, [metrics]);

  const providerOptions = useMemo(() => Array.from(new Set(alignment.map((item) => item.market_provider))).sort(), [alignment]);
  const categoryOptions = useMemo(() => Array.from(new Set(alignment.map((item) => item.market_category))).sort(), [alignment]);
  const modelModeOptions = useMemo(() => Array.from(new Set(alignment.map((item) => String(item.metadata.model_mode ?? 'unknown')))).sort(), [alignment]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Quantitative evaluation runtime"
        title="Evaluation"
        description="Auditable ex-post board for calibration and effectiveness. Local-first, manual-first, paper/sandbox only. No opaque auto-tuning."
        actions={<div className="button-row"><button type="button" className="secondary-button" onClick={() => void onRunRuntimeEvaluation()} disabled={isRunning}>{isRunning ? 'Running...' : 'Run runtime evaluation'}</button><button type="button" className="ghost-button" onClick={() => navigate('/tuning')}>Open tuning board</button></div>}
      />

      <DataStateWrapper isLoading={isLoading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        {!summary?.latest_run ? (
          <EmptyState
            eyebrow="No runtime records"
            title="No resolved evaluation records are available yet"
            description="No resolved evaluation records are available yet. Run runtime evaluation to measure calibration and effectiveness."
          />
        ) : (
          <>
            <SectionCard eyebrow="Summary" title="Runtime summary" description="Top-level quantitative health and manual review signal.">
              <div className="system-metadata-grid">
                <div><strong>Resolved markets:</strong> {summary.latest_run.resolved_market_count}</div>
                <div><strong>Linked predictions:</strong> {summary.latest_run.linked_prediction_count}</div>
                <div><strong>Calibration buckets:</strong> {summary.latest_run.calibration_bucket_count}</div>
                <div><strong>Poor metrics:</strong> {poorMetrics}</div>
                <div><strong>Drift flags:</strong> {summary.latest_run.drift_flag_count}</div>
                <div><strong>Manual review required:</strong> <StatusBadge tone={summary.manual_review_required ? 'pending' : 'ready'}>{summary.manual_review_required ? 'YES' : 'NO'}</StatusBadge></div>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Actions" title="Filters" description="Filter records by provider/category/model mode/alignment status.">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(160px, 1fr))', gap: '0.75rem' }}>
                <select value={providerFilter} onChange={(event) => setProviderFilter(event.target.value)}><option value="">All providers</option>{providerOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>
                <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option value="">All categories</option>{categoryOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>
                <select value={modelModeFilter} onChange={(event) => setModelModeFilter(event.target.value)}><option value="">All model modes</option>{modelModeOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>
                <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="">All alignment status</option>
                  <option value="WELL_CALIBRATED">WELL_CALIBRATED</option>
                  <option value="OVERCONFIDENT">OVERCONFIDENT</option>
                  <option value="UNDERCONFIDENT">UNDERCONFIDENT</option>
                  <option value="GOOD_SKIP">GOOD_SKIP</option>
                  <option value="BAD_SKIP">BAD_SKIP</option>
                  <option value="NO_EDGE_REALIZED">NO_EDGE_REALIZED</option>
                  <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
                </select>
              </div>
            </SectionCard>

            <SectionCard eyebrow="Outcome alignment" title="Prediction/risk/proposal vs realized outcome" description="Ex-post alignment records with traceable links.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Market</th><th>Provider</th><th>Calibrated prob</th><th>Market prob</th><th>Realized outcome</th><th>Adjusted edge</th><th>Alignment</th><th>Links</th></tr></thead><tbody>
                {alignment.map((item) => (
                  <tr key={item.id}>
                    <td>{item.market_title}</td>
                    <td>{item.market_provider}</td>
                    <td>{toPercent(item.calibrated_probability_at_decision)}</td>
                    <td>{toPercent(item.market_probability_at_decision)}</td>
                    <td>{item.resolved_outcome}</td>
                    <td>{item.adjusted_edge_at_decision ?? 'n/a'}</td>
                    <td><StatusBadge tone={alignmentTone[item.alignment_status] ?? 'neutral'}>{item.alignment_status}</StatusBadge></td>
                    <td>P:{item.linked_prediction_assessment ?? '-'} / R:{item.linked_risk_approval ?? '-'} / O:{item.linked_opportunity_assessment ?? '-'} / PP:{item.linked_paper_proposal ?? '-'}</td>
                  </tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Calibration" title="Calibration buckets" description="Probability bucket quality by segment.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Bucket</th><th>Sample</th><th>Mean predicted</th><th>Hit rate</th><th>Gap</th><th>Scope</th><th>Value</th></tr></thead><tbody>
                {buckets.map((item) => (
                  <tr key={item.id}><td>{item.bucket_label}</td><td>{item.sample_count}</td><td>{toPercent(item.mean_predicted_probability)}</td><td>{toPercent(item.empirical_hit_rate)}</td><td>{toPercent(item.calibration_gap)}</td><td>{item.segment_scope}</td><td>{item.segment_value}</td></tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Effectiveness" title="Funnel and gate quality metrics" description="Global and segmented effectiveness indicators.">
              <div className="table-wrapper"><table className="data-table"><thead><tr><th>Metric type</th><th>Scope</th><th>Value</th><th>Sample</th><th>Status</th><th>Interpretation</th></tr></thead><tbody>
                {metrics.map((item) => (
                  <tr key={item.id}><td>{item.metric_type}</td><td>{item.metric_scope}</td><td>{item.metric_value}</td><td>{item.sample_count}</td><td><StatusBadge tone={metricTone[item.status] ?? 'neutral'}>{item.status}</StatusBadge></td><td>{item.interpretation}</td></tr>
                ))}
              </tbody></table></div>
            </SectionCard>

            <SectionCard eyebrow="Recommendations" title="Human review recommendations" description="Explicit review actions; no automatic policy or model changes.">
              {recommendations.length ? (
                <ul>
                  {recommendations.map((item) => (
                    <li key={item.id}><strong>{item.recommendation_type}</strong> — {item.rationale} (confidence {toPercent(item.confidence)})</li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  eyebrow="No recommendations"
                  title="No explicit recommendations generated"
                  description="Current evaluation run did not raise recommendation thresholds."
                />
              )}
            </SectionCard>
          </>
        )}
      </DataStateWrapper>
    </div>
  );
}
