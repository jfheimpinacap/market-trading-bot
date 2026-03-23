import type { ChangeEvent } from 'react';
import type { MockAgent, SignalFilters } from '../../types/signals';

type SignalsFiltersProps = {
  filters: SignalFilters;
  agents: MockAgent[];
  onChange: (nextFilters: SignalFilters) => void;
  onReset: () => void;
};

const signalTypeOptions = ['', 'OPPORTUNITY', 'MOMENTUM', 'MEAN_REVERSION', 'EXTREME', 'RISK', 'DORMANT'];
const statusOptions = ['', 'ACTIVE', 'MONITOR', 'EXPIRED', 'SUPERSEDED'];
const directionOptions = ['', 'BULLISH', 'BEARISH', 'NEUTRAL'];
const actionableOptions = [
  { value: '', label: 'All actionability states' },
  { value: 'true', label: 'Actionable only' },
  { value: 'false', label: 'Not actionable only' },
];
const orderingOptions = [
  { value: '-created_at', label: 'Newest first' },
  { value: 'created_at', label: 'Oldest first' },
  { value: '-score', label: 'Score · highest first' },
  { value: '-confidence', label: 'Confidence · highest first' },
];

export function SignalsFilters({ filters, agents, onChange, onReset }: SignalsFiltersProps) {
  function handleFieldChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.target;
    onChange({ ...filters, [name]: value });
  }

  return (
    <section className="panel markets-filters">
      <div className="markets-filters__header">
        <div>
          <p className="section-label">Filters</p>
          <h3>Refine the demo signals queue</h3>
          <p>Filter by market id, mock agent, signal type, direction, lifecycle status, or actionability.</p>
        </div>
        <div className="markets-filters__actions">
          <span className="muted-text">{agents.length} mock agents available</span>
          <button className="secondary-button" type="button" onClick={onReset}>
            Reset filters
          </button>
        </div>
      </div>

      <div className="markets-filters__grid">
        <label className="field-group">
          <span>Market id</span>
          <input
            className="text-input"
            name="market"
            type="search"
            placeholder="Optional market id"
            value={filters.market}
            onChange={handleFieldChange}
          />
        </label>

        <label className="field-group">
          <span>Agent</span>
          <select className="select-input" name="agent" value={filters.agent} onChange={handleFieldChange}>
            <option value="">All agents</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.slug}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Signal type</span>
          <select className="select-input" name="signal_type" value={filters.signal_type} onChange={handleFieldChange}>
            {signalTypeOptions.map((signalType) => (
              <option key={signalType || 'all'} value={signalType}>
                {signalType ? signalType.replace(/_/g, ' ') : 'All signal types'}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Status</span>
          <select className="select-input" name="status" value={filters.status} onChange={handleFieldChange}>
            {statusOptions.map((status) => (
              <option key={status || 'all'} value={status}>
                {status || 'All statuses'}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Direction</span>
          <select className="select-input" name="direction" value={filters.direction} onChange={handleFieldChange}>
            {directionOptions.map((direction) => (
              <option key={direction || 'all'} value={direction}>
                {direction || 'All directions'}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Actionable</span>
          <select className="select-input" name="is_actionable" value={filters.is_actionable} onChange={handleFieldChange}>
            {actionableOptions.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Ordering</span>
          <select className="select-input" name="ordering" value={filters.ordering} onChange={handleFieldChange}>
            {orderingOptions.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
