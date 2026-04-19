import { useCallback, useEffect, useMemo, useState } from 'react';

import { PageHeader } from '../components/PageHeader';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/dashboard/StatusBadge';
import { DataStateWrapper } from '../components/markets/DataStateWrapper';
import { useSystemHealth } from '../app/SystemHealthProvider';
import { PROJECT_NAME } from '../lib/config';
import { navigate } from '../lib/router';
import { getCockpitAttention, getCockpitSummary } from '../services/cockpit';
import { getTestConsoleStatus } from '../services/missionControl';
import { getPaperSnapshots, getPaperSummary } from '../services/paperTrading';
import type { CockpitAttentionItem } from '../types/cockpit';
import type { LlmAuxSignalSummary, TestConsoleStatusResponse } from '../types/missionControl';
import type { PaperPortfolioSnapshot, PaperPortfolioSummary } from '../types/paperTrading';

const toNumber = (value: string | null | undefined) => {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatMoney = (value: string | null | undefined) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'n/a';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(parsed);
};

const formatSignedMoney = (value: string | null | undefined) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'n/a';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
    signDisplay: 'always',
  }).format(parsed);
};

const formatTimestamp = (value: string | null | undefined) => {
  if (!value) return 'n/a';
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
};

const statusTone = (status: string | null | undefined): 'ready' | 'pending' | 'offline' | 'neutral' => {
  const normalized = (status ?? '').toUpperCase();
  if (['ACTIVE', 'READY', 'RUNNING', 'PASS', 'ALLOW', 'NORMAL', 'NO_ACTION', 'HEALTHY'].includes(normalized)) return 'ready';
  if (['PAUSED', 'WARNING', 'WARN', 'ALLOW_WITH_CAUTION', 'REVIEW_SOON', 'MONITOR_ONLY', 'CAUTION', 'DEGRADED'].includes(normalized)) return 'pending';
  if (['STOPPED', 'BLOCKED', 'FAIL', 'BLOCK', 'REVIEW_NOW'].includes(normalized)) return 'offline';
  return 'neutral';
};

const getExecutivePhrase = (status: TestConsoleStatusResponse | null) => {
  if (!status) return 'Sin snapshot operativo reciente';
  if (status.gate_status === 'BLOCK' || status.validation_status === 'BLOCKED') {
    return 'Bloqueado: requiere revisión';
  }
  if (status.attention_mode === 'REVIEW_NOW' || status.attention_mode === 'REVIEW_SOON') {
    return 'Cautela: revisión sugerida';
  }
  if (status.test_status?.toUpperCase() === 'RUNNING') {
    return 'Operativo: monitoreo activo';
  }
  return 'Operativo estable';
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

function MiniTrendChart({
  points,
  label,
  color,
}: {
  points: Array<{ xLabel: string; value: number | null }>;
  label: string;
  color: string;
}) {
  const usable = points.filter((point): point is { xLabel: string; value: number } => point.value !== null);
  if (usable.length < 2) {
    return <p className="muted-text">Sin historial para {label.toLowerCase()}.</p>;
  }

  const min = Math.min(...usable.map((point) => point.value));
  const max = Math.max(...usable.map((point) => point.value));
  const range = Math.max(max - min, 1);
  const polyline = usable
    .map((point, index) => {
      const x = (index / Math.max(usable.length - 1, 1)) * 100;
      const y = 100 - ((point.value - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="executive-chart">
      <div className="executive-chart__header">
        <strong>{label}</strong>
        <span className="muted-text">{usable[usable.length - 1].xLabel}</span>
      </div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label={`${label} trend`}>
        <polyline points={polyline} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

export function DashboardPage() {
  const health = useSystemHealth();
  const [paperSummary, setPaperSummary] = useState<PaperPortfolioSummary | null>(null);
  const [paperSnapshots, setPaperSnapshots] = useState<PaperPortfolioSnapshot[]>([]);
  const [paperLoading, setPaperLoading] = useState(true);
  const [paperError, setPaperError] = useState<string | null>(null);
  const [testConsoleStatus, setTestConsoleStatus] = useState<TestConsoleStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [attentionItems, setAttentionItems] = useState<CockpitAttentionItem[]>([]);
  const [attentionLoading, setAttentionLoading] = useState(true);
  const [attentionError, setAttentionError] = useState<string | null>(null);

  const loadExecutiveData = useCallback(async () => {
    setPaperLoading(true);
    setPaperError(null);
    setStatusLoading(true);
    setStatusError(null);
    setAttentionLoading(true);
    setAttentionError(null);

    await Promise.all([
      (async () => {
        try {
          const [summary, snapshots] = await Promise.all([getPaperSummary(), getPaperSnapshots()]);
          setPaperSummary(summary);
          setPaperSnapshots(snapshots.slice(-12));
        } catch (error) {
          setPaperSummary(null);
          setPaperSnapshots([]);
          setPaperError(getErrorMessage(error, 'No se pudo cargar el estado paper.'));
        } finally {
          setPaperLoading(false);
        }
      })(),
      (async () => {
        try {
          const response = await getTestConsoleStatus();
          setTestConsoleStatus(response);
        } catch (error) {
          setTestConsoleStatus(null);
          setStatusError(getErrorMessage(error, 'No se pudo cargar el estado operativo.'));
        } finally {
          setStatusLoading(false);
        }
      })(),
      (async () => {
        try {
          const snapshot = await getCockpitSummary();
          const response = getCockpitAttention(snapshot);
          setAttentionItems(response.slice(0, 3));
        } catch (error) {
          setAttentionItems([]);
          setAttentionError(getErrorMessage(error, 'No se pudieron cargar alertas priorizadas.'));
        } finally {
          setAttentionLoading(false);
        }
      })(),
    ]);
  }, []);

  useEffect(() => {
    void loadExecutiveData();
  }, [loadExecutiveData]);

  const executiveTone = statusTone(testConsoleStatus?.validation_status ?? health.backendStatus);
  const llmHint = testConsoleStatus?.llm_aux_signal_summary ?? null;

  const quickState = useMemo(
    () => [
      { label: 'Bot', value: testConsoleStatus?.test_status ?? 'Sin dato', tone: statusTone(testConsoleStatus?.test_status) },
      { label: 'Funnel', value: testConsoleStatus?.funnel_status ?? 'Sin dato', tone: statusTone(testConsoleStatus?.funnel_status) },
      { label: 'Validation', value: testConsoleStatus?.validation_status ?? 'Sin dato', tone: statusTone(testConsoleStatus?.validation_status) },
      { label: 'Gate', value: testConsoleStatus?.gate_status ?? 'Sin dato', tone: statusTone(testConsoleStatus?.gate_status) },
      { label: 'Trial', value: testConsoleStatus?.trial_status ?? 'Sin dato', tone: statusTone(testConsoleStatus?.trial_status) },
      { label: 'Attention', value: testConsoleStatus?.attention_mode ?? 'Sin dato', tone: statusTone(testConsoleStatus?.attention_mode) },
    ],
    [testConsoleStatus],
  );

  const kpis = useMemo(
    () => [
      { label: 'Capital', value: formatMoney(paperSummary?.account.equity) },
      { label: 'Cash', value: formatMoney(paperSummary?.account.cash_balance) },
      { label: 'PnL U', value: formatSignedMoney(paperSummary?.account.unrealized_pnl) },
      { label: 'PnL R', value: formatSignedMoney(paperSummary?.account.realized_pnl) },
      { label: 'Posiciones', value: String(paperSummary?.open_positions_count ?? 0) },
      { label: 'Trades', value: String(paperSummary?.recent_trades.length ?? 0) },
    ],
    [paperSummary],
  );

  const equityPoints = useMemo(
    () => paperSnapshots.map((snapshot) => ({ xLabel: formatTimestamp(snapshot.captured_at), value: toNumber(snapshot.equity) })),
    [paperSnapshots],
  );

  const pnlPoints = useMemo(
    () => paperSnapshots.map((snapshot) => ({ xLabel: formatTimestamp(snapshot.captured_at), value: toNumber(snapshot.total_pnl) })),
    [paperSnapshots],
  );

  const latestTrade = paperSummary?.recent_trades[0] ?? null;
  const priorityAttentionItems = attentionItems.slice(0, 2);
  const remainingAttentionItems = attentionItems.slice(2);
  const hasCriticalAttention = attentionItems.some((item) => item.severity === 'CRITICAL' || item.severity === 'HIGH');
  const exposureBlock = testConsoleStatus?.blocker_summary ?? (testConsoleStatus?.gate_status === 'BLOCK' ? 'Gate bloqueado' : 'Sin bloqueo dominante');

  return (
    <div className="page-stack dashboard-page executive-dashboard-page">
      <PageHeader
        title={`${PROJECT_NAME} · Dashboard`}
        actions={(
          <div className="button-row">
            <StatusBadge tone={executiveTone}>{getExecutivePhrase(testConsoleStatus)}</StatusBadge>
            <details className="dashboard-inline-actions">
              <summary>Más</summary>
              <div className="button-row">
                <button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Vista avanzada</button>
              </div>
            </details>
          </div>
        )}
      />

      <section className="dashboard-quick-strip" aria-label="Estado rápido">
        {quickState.map((item) => (
          <article key={item.label} className="dashboard-quick-pill" title={`${item.label}: ${item.value}`}>
            <span>{item.label}</span>
            <StatusBadge tone={item.tone}>{item.value}</StatusBadge>
          </article>
        ))}
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard eyebrow="Operator-first" title="Resumen de operación actual" aside={<StatusBadge tone={hasCriticalAttention ? 'offline' : 'ready'}>{hasCriticalAttention ? 'Review requerida' : 'Sin crítico'}</StatusBadge>}>
          <DataStateWrapper
            isLoading={statusLoading}
            isError={Boolean(statusError)}
            errorMessage={statusError ?? undefined}
            loadingTitle="Cargando estado operativo"
            loadingDescription="Consolidando status del test console."
            errorTitle="No se pudo cargar el estado operativo"
          >
            <dl className="dashboard-key-value-list dashboard-key-value-list--compact">
              <div><dt>Última señal útil</dt><dd>{getLlmHintText(llmHint)}</dd></div>
              <div><dt>Exposición activa</dt><dd>{paperSummary?.open_positions_count ?? 0} abiertas</dd></div>
              <div><dt>Bloqueo relevante</dt><dd>{exposureBlock}</dd></div>
              <div><dt>Último trade</dt><dd>{latestTrade ? `${latestTrade.side} ${latestTrade.market__title}` : 'Sin trades'}</dd></div>
            </dl>
            <details className="dashboard-secondary-details">
              <summary>Contexto adicional</summary>
              <p className="muted-text">Último evento: {testConsoleStatus?.last_event ?? 'n/a'}</p>
              <p className="muted-text">Hora último trade: {latestTrade ? formatTimestamp(latestTrade.executed_at) : 'n/a'}</p>
              <p className="muted-text">{testConsoleStatus?.next_action_hint ?? 'Sin recomendaciones inmediatas.'}</p>
              {testConsoleStatus?.last_reason_code ? <p className="muted-text">Código: {testConsoleStatus.last_reason_code}</p> : null}
            </details>
          </DataStateWrapper>
        </SectionCard>

        <SectionCard
          eyebrow="Attention"
          title="Warnings y foco de revisión"
          aside={<StatusBadge tone={statusTone(testConsoleStatus?.attention_mode)}>{testConsoleStatus?.attention_mode ?? 'Sin dato'}</StatusBadge>}
        >
          <DataStateWrapper
            isLoading={attentionLoading}
            isError={Boolean(attentionError)}
            errorMessage={attentionError ?? undefined}
            loadingTitle="Cargando alertas"
            loadingDescription="Consultando prioridades actuales."
            errorTitle="No se pudieron cargar alertas"
          >
            <ul className="bullet-list compact-list">
              {attentionItems.length === 0 ? <li>Sin items prioritarios.</li> : null}
              {priorityAttentionItems.map((item) => (
                <li key={item.id}>
                  <strong>{item.severity}:</strong> {item.title}
                </li>
              ))}
            </ul>
            <details className="dashboard-secondary-details">
              <summary>Resumen auxiliar</summary>
              {remainingAttentionItems.length > 0 ? (
                <ul className="bullet-list compact-list">
                  {remainingAttentionItems.map((item) => (
                    <li key={item.id}>
                      <strong>{item.severity}:</strong> {item.title}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="executive-llm-hint">
                {llmHint?.aux_signal_status ? `(${llmHint.aux_signal_status})` : '(sin señal)'} {getLlmHintText(llmHint)}
              </div>
            </details>
          </DataStateWrapper>
        </SectionCard>
      </section>

      <SectionCard eyebrow="KPIs" title="Fila compacta de capital" description="Visión rápida; detalle técnico plegado.">
        <DataStateWrapper
          isLoading={paperLoading}
          isError={Boolean(paperError)}
          errorMessage={paperError ?? undefined}
          loadingTitle="Cargando KPIs paper"
          loadingDescription="Consultando summary de portafolio paper."
          errorTitle="No se pudieron cargar los KPIs"
        >
          <div className="dashboard-stat-grid dashboard-stat-grid--compact">
            {kpis.map((kpi) => (
              <article key={kpi.label} className="dashboard-stat-card dashboard-stat-card--tight" title={kpi.label}>
                <span>{kpi.label}</span>
                <strong>{kpi.value}</strong>
              </article>
            ))}
          </div>
          <details className="dashboard-secondary-details">
            <summary>Ver detalle financiero</summary>
            <div className="content-grid content-grid--two-columns dashboard-trend-grid">
              <MiniTrendChart points={equityPoints} label="Equity" color="#5e9dff" />
              <MiniTrendChart points={pnlPoints} label="Total PnL" color="#35c58a" />
            </div>
          </details>
        </DataStateWrapper>
      </SectionCard>

      <details className="dashboard-secondary-details dashboard-routing-details">
        <summary>Ir a detalle técnico (avanzado)</summary>
        <ul className="bullet-list compact-list">
          <li>Cockpit: funnel, bloqueos técnicos, diagnósticos y trazas.</li>
          <li>Mission Control: trial/gate y controles operativos.</li>
          <li>Runtime/Trace: investigación profunda y auditoría.</li>
        </ul>
        <div className="button-row">
          <button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Abrir vista avanzada</button>
        </div>
      </details>
    </div>
  );
}

function getLlmHintText(summary: LlmAuxSignalSummary | null) {
  if (!summary?.enabled) return 'Sin alerta auxiliar';
  if (summary.aux_signal_recommendation) return summary.aux_signal_recommendation;
  if (summary.summary) return summary.summary;
  return 'Señal auxiliar disponible en vista avanzada';
}
