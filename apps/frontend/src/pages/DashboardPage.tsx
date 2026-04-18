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
  if (['ACTIVE', 'READY', 'RUNNING', 'PASS', 'ALLOW', 'NORMAL', 'NO_ACTION'].includes(normalized)) return 'ready';
  if (['PAUSED', 'WARNING', 'WARN', 'ALLOW_WITH_CAUTION', 'REVIEW_SOON', 'MONITOR_ONLY', 'CAUTION'].includes(normalized)) return 'pending';
  if (['STOPPED', 'BLOCKED', 'FAIL', 'BLOCK', 'REVIEW_NOW'].includes(normalized)) return 'offline';
  return 'neutral';
};

const getExecutivePhrase = (status: TestConsoleStatusResponse | null) => {
  if (!status) return 'Sin datos operativos recientes. Revisar consola avanzada.';
  if (status.gate_status === 'BLOCK' || status.validation_status === 'BLOCKED') {
    return 'En revisión: hay bloqueos que requieren atención antes de continuar.';
  }
  if (status.attention_mode === 'REVIEW_NOW' || status.attention_mode === 'REVIEW_SOON') {
    return 'Operando con cautela: se recomienda revisión manual.';
  }
  if (status.test_status?.toUpperCase() === 'RUNNING') {
    return 'Funcionando normal: monitoreo activo en curso.';
  }
  return 'Funcionando estable en modo paper con supervisión.';
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
    return <p className="muted-text">Sin historial suficiente para ver la tendencia de {label.toLowerCase()} todavía.</p>;
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
          setAttentionItems(response.slice(0, 4));
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

  const kpis = useMemo(
    () => [
      { label: 'Capital total', value: formatMoney(paperSummary?.account.equity) },
      { label: 'Saldo disponible', value: formatMoney(paperSummary?.account.cash_balance) },
      { label: 'Resultado no realizado', value: formatSignedMoney(paperSummary?.account.unrealized_pnl) },
      { label: 'Resultado realizado', value: formatSignedMoney(paperSummary?.account.realized_pnl) },
      { label: 'Posiciones abiertas', value: String(paperSummary?.open_positions_count ?? 0) },
      { label: 'Operaciones recientes', value: String(paperSummary?.recent_trades.length ?? 0) },
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
  const hasCriticalAttention = attentionItems.some((item) => item.severity === 'CRITICAL' || item.severity === 'HIGH');

  return (
    <div className="page-stack dashboard-page executive-dashboard-page">
      <PageHeader
        title={`${PROJECT_NAME} · Dashboard`}
        actions={(
          <div className="button-row">
            <button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Vista avanzada</button>
            <StatusBadge tone={executiveTone}>{getExecutivePhrase(testConsoleStatus)}</StatusBadge>
          </div>
        )}
      />

      <section className="content-grid content-grid--two-columns">
        <SectionCard
          eyebrow="Estado general"
          title="Salud operativa del bot"
        >
          <DataStateWrapper
            isLoading={statusLoading}
            isError={Boolean(statusError)}
            errorMessage={statusError ?? undefined}
            loadingTitle="Cargando estado operativo"
            loadingDescription="Consultando estado consolidado del test console."
            errorTitle="No se pudo cargar el estado operativo"
          >
            <dl className="dashboard-key-value-list">
              <div><dt>Estado del bot</dt><dd><StatusBadge tone={statusTone(testConsoleStatus?.test_status)}>{testConsoleStatus?.test_status ?? 'Sin dato'}</StatusBadge></dd></div>
              <div><dt>Validación</dt><dd><StatusBadge tone={statusTone(testConsoleStatus?.validation_status)}>{testConsoleStatus?.validation_status ?? 'Sin dato'}</StatusBadge></dd></div>
              <div><dt>Permiso operativo</dt><dd><StatusBadge tone={statusTone(testConsoleStatus?.gate_status)}>{testConsoleStatus?.gate_status ?? 'Sin dato'}</StatusBadge></dd></div>
              <div><dt>Nivel de atención</dt><dd><StatusBadge tone={statusTone(testConsoleStatus?.attention_mode)}>{testConsoleStatus?.attention_mode ?? 'Sin dato'}</StatusBadge></dd></div>
            </dl>
            <details className="dashboard-secondary-details">
              <summary>Ver detalle operativo</summary>
              <dl className="dashboard-key-value-list dashboard-key-value-list--secondary">
                <div><dt>Flujo operativo</dt><dd>{testConsoleStatus?.funnel_status ?? 'Sin dato'}</dd></div>
                <div><dt>Última actualización</dt><dd>{formatTimestamp(testConsoleStatus?.updated_at ?? testConsoleStatus?.started_at)}</dd></div>
              </dl>
            </details>
          </DataStateWrapper>
        </SectionCard>

        <SectionCard
          eyebrow="Navegación"
          title="Detalle técnico"
          description="La complejidad diagnóstica permanece en la vista avanzada."
          aside={<StatusBadge tone="neutral">Modo operador</StatusBadge>}
        >
          <ul className="bullet-list compact-list">
            <li>Cockpit (advanced): funnel, bloques técnicos, diagnósticos LLM y export detallado.</li>
            <li>Mission Control: trial, gate y controles operativos.</li>
            <li>Runtime / Trace: investigación profunda y auditoría de decisiones.</li>
          </ul>
          <div className="button-row">
            <button type="button" className="secondary-button" onClick={() => navigate('/cockpit')}>Ir a vista avanzada</button>
          </div>
        </SectionCard>
      </section>

      <SectionCard eyebrow="Resumen financiero" title="Capital y resultado" description="Métricas clave para saber si el bot gana, pierde o se mantiene estable.">
        <DataStateWrapper
          isLoading={paperLoading}
          isError={Boolean(paperError)}
          errorMessage={paperError ?? undefined}
          loadingTitle="Cargando KPIs paper"
          loadingDescription="Consultando summary de portafolio paper."
          errorTitle="No se pudieron cargar los KPIs"
        >
          <div className="dashboard-stat-grid">
            {kpis.map((kpi) => (
              <article key={kpi.label} className="dashboard-stat-card">
                <span>{kpi.label}</span>
                <strong>{kpi.value}</strong>
              </article>
            ))}
          </div>
        </DataStateWrapper>
      </SectionCard>

      <section className="content-grid content-grid--two-columns">
        <SectionCard eyebrow="Tendencia" title="Capital reciente">
          <DataStateWrapper
            isLoading={paperLoading}
            isError={Boolean(paperError)}
            errorMessage={paperError ?? undefined}
            loadingTitle="Cargando tendencia"
            loadingDescription="Preparando serie de snapshots de equity."
            errorTitle="No se pudo mostrar la tendencia"
          >
            <MiniTrendChart points={equityPoints} label="Equity" color="#5e9dff" />
          </DataStateWrapper>
        </SectionCard>

        <SectionCard eyebrow="Tendencia" title="Ganancia/Pérdida reciente">
          <DataStateWrapper
            isLoading={paperLoading}
            isError={Boolean(paperError)}
            errorMessage={paperError ?? undefined}
            loadingTitle="Cargando tendencia"
            loadingDescription="Preparando serie de snapshots de PnL."
            errorTitle="No se pudo mostrar la tendencia"
          >
            <MiniTrendChart points={pnlPoints} label="Total PnL" color="#35c58a" />
          </DataStateWrapper>
        </SectionCard>
      </section>

      <section className="content-grid content-grid--two-columns">
        <SectionCard eyebrow="Actividad reciente" title="Qué hizo el bot" description="Última acción relevante y último trade ejecutado.">
          <DataStateWrapper
            isLoading={paperLoading || statusLoading}
            isError={Boolean(paperError) || Boolean(statusError)}
            errorMessage={paperError ?? statusError ?? undefined}
            loadingTitle="Cargando actividad"
            loadingDescription="Unificando últimos eventos operativos y trades recientes."
            errorTitle="No se pudo cargar actividad reciente"
          >
            <dl className="dashboard-key-value-list">
              <div><dt>Último evento operativo</dt><dd>{testConsoleStatus?.last_event ?? 'n/a'}</dd></div>
              <div><dt>Última acción de mercado</dt><dd>{latestTrade ? `${latestTrade.trade_type} ${latestTrade.side} · ${latestTrade.market__title}` : 'Sin trades recientes'}</dd></div>
              <div><dt>Hora último trade</dt><dd>{latestTrade ? formatTimestamp(latestTrade.executed_at) : 'n/a'}</dd></div>
              <div><dt>Resumen corto</dt><dd>{testConsoleStatus?.next_action_hint ?? 'Sin acciones sugeridas por ahora.'}</dd></div>
            </dl>
            {testConsoleStatus?.last_reason_code ? (
              <details className="dashboard-secondary-details">
                <summary>Ver motivo técnico</summary>
                <p className="muted-text">{testConsoleStatus.last_reason_code}</p>
              </details>
            ) : null}
          </DataStateWrapper>
        </SectionCard>

        <SectionCard
          eyebrow="Alertas y revisión"
          title="Atención prioritaria"
          description="Solo señales de revisión importantes y un hint auxiliar LLM resumido."
          aside={<StatusBadge tone={hasCriticalAttention ? 'offline' : 'ready'}>{hasCriticalAttention ? 'Revisión requerida' : 'Sin alertas críticas'}</StatusBadge>}
        >
          <DataStateWrapper
            isLoading={attentionLoading}
            isError={Boolean(attentionError)}
            errorMessage={attentionError ?? undefined}
            loadingTitle="Cargando alertas"
            loadingDescription="Consultando elementos de atención priorizada del cockpit."
            errorTitle="No se pudieron cargar alertas"
          >
            <ul className="bullet-list compact-list">
              {attentionItems.length === 0 ? <li>Sin items prioritarios en este momento.</li> : null}
              {attentionItems.map((item) => (
                <li key={item.id}>
                  <strong>{item.severity}:</strong> {item.title} — {item.summary}
                </li>
              ))}
            </ul>
            <details className="dashboard-secondary-details">
              <summary>Hint auxiliar LLM</summary>
              <div className="executive-llm-hint">
                {llmHint?.aux_signal_status ? `(${llmHint.aux_signal_status})` : '(sin señal)'} {getLlmHintText(llmHint)}
              </div>
            </details>
          </DataStateWrapper>
        </SectionCard>
      </section>
    </div>
  );
}

function getLlmHintText(summary: LlmAuxSignalSummary | null) {
  if (!summary?.enabled) return 'sin alerta auxiliar.';
  if (summary.aux_signal_recommendation) return summary.aux_signal_recommendation.toLowerCase();
  if (summary.summary) return summary.summary;
  return 'señal auxiliar disponible en vista avanzada.';
}
