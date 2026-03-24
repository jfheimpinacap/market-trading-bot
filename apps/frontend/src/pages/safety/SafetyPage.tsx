import { useCallback, useEffect, useState } from 'react';
import { DataStateWrapper } from '../../components/markets/DataStateWrapper';
import { PageHeader } from '../../components/PageHeader';
import { SectionCard } from '../../components/SectionCard';
import { StatusBadge } from '../../components/dashboard/StatusBadge';
import { navigate } from '../../lib/router';
import {
  disableKillSwitch,
  enableKillSwitch,
  getSafetyConfig,
  getSafetyEvents,
  getSafetyStatus,
  resetSafetyCooldown,
} from '../../services/safety';
import type { SafetyConfig, SafetyEvent, SafetyStatus } from '../../types/safety';

function tone(value: string) {
  if (value === 'HEALTHY') return 'ready';
  if (value === 'WARNING' || value === 'COOLDOWN' || value === 'PAUSED') return 'pending';
  if (value === 'HARD_STOP' || value === 'KILL_SWITCH') return 'offline';
  return 'neutral';
}

export function SafetyPage() {
  const [status, setStatus] = useState<SafetyStatus | null>(null);
  const [config, setConfig] = useState<SafetyConfig | null>(null);
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, configResponse, eventsResponse] = await Promise.all([getSafetyStatus(), getSafetyConfig(), getSafetyEvents()]);
      setStatus(statusResponse);
      setConfig(configResponse);
      setEvents(eventsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load safety status.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const trigger = useCallback(async (fn: () => Promise<unknown>) => {
    await fn();
    await load();
  }, [load]);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Safety hardening"
        title="Safety"
        description="Guardrails operativos para paper/demo only: límites, cooldown, hard-stop y kill switch auditables."
        actions={<button type="button" className="secondary-button" onClick={() => navigate('/continuous-demo')}>Open Continuous Demo</button>}
      />

      <DataStateWrapper isLoading={loading} isError={Boolean(error)} errorMessage={error ?? undefined}>
        <SectionCard eyebrow="Current status" title="Safety state" description="Estado consolidado de salud operativa y último evento de seguridad.">
          <div className="system-metadata-grid">
            <div><strong>Status:</strong> <StatusBadge tone={tone(status?.status ?? 'UNKNOWN')}>{status?.status ?? 'UNKNOWN'}</StatusBadge></div>
            <div><strong>Kill switch:</strong> {status?.kill_switch_enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Hard stop:</strong> {status?.hard_stop_active ? 'Active' : 'Inactive'}</div>
            <div><strong>Cooldown until cycle:</strong> {status?.cooldown_until_cycle ?? 'No cooldown'}</div>
            <div><strong>Message:</strong> {status?.status_message || 'No active safety message.'}</div>
            <div><strong>Last event:</strong> {status?.last_event ? `${status.last_event.event_type} · ${status.last_event.message}` : 'No events yet.'}</div>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Limits" title="Configured guardrails" description="Límites explícitos que afectan auto ejecución y control del loop.">
          <ul>
            <li>Max auto trades per cycle: {config?.max_auto_trades_per_cycle ?? '-'}</li>
            <li>Max auto trades per session: {config?.max_auto_trades_per_session ?? '-'}</li>
            <li>Max position exposure per market: {config?.max_position_value_per_market ?? '-'}</li>
            <li>Max total open exposure: {config?.max_total_open_exposure ?? '-'}</li>
            <li>Max drawdown per session: {config?.max_daily_or_session_drawdown ?? '-'}</li>
            <li>Max unrealized loss threshold: {config?.max_unrealized_loss_threshold ?? '-'}</li>
            <li>Cooldown trigger blocks: {config?.cooldown_after_block_count ?? '-'}</li>
            <li>Cooldown cycles: {config?.cooldown_cycles ?? '-'}</li>
          </ul>
        </SectionCard>

        <SectionCard eyebrow="Kill switch" title="Critical controls" description="Controles manuales explícitos. Kill switch bloquea autoejecución y nuevos ciclos.">
          <div className="button-row">
            <button type="button" className="ghost-button" onClick={() => void trigger(enableKillSwitch)}>Enable kill switch</button>
            <button type="button" className="secondary-button" onClick={() => void trigger(disableKillSwitch)}>Disable kill switch</button>
            <button type="button" className="secondary-button" onClick={() => void trigger(resetSafetyCooldown)}>Reset cooldown</button>
          </div>
          <p>Estas acciones permanecen manuales por diseño para operar de forma conservadora.</p>
        </SectionCard>

        <SectionCard eyebrow="Events" title="Recent safety events" description="Trazabilidad operativa para auditoría de warnings, pausas y stops.">
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Source</th>
                  <th>Message</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {events.slice(0, 20).map((event) => (
                  <tr key={event.id}>
                    <td>{event.event_type}</td>
                    <td><StatusBadge tone={event.severity === 'CRITICAL' ? 'offline' : event.severity === 'WARNING' ? 'pending' : 'neutral'}>{event.severity}</StatusBadge></td>
                    <td>{event.source}</td>
                    <td>{event.message}</td>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </DataStateWrapper>
    </div>
  );
}
