import type { ChangeEvent } from 'react';
import type { MarketEvent, MarketFilters, MarketProvider } from '../../types/markets';

type MarketsFiltersProps = {
  filters: MarketFilters;
  providers: MarketProvider[];
  events: MarketEvent[];
  onChange: (nextFilters: MarketFilters) => void;
  onReset: () => void;
};

const statusOptions = ['', 'open', 'paused', 'closed', 'resolved', 'cancelled'];
const activeOptions = [
  { value: '', label: 'All activity states' },
  { value: 'true', label: 'Active only' },
  { value: 'false', label: 'Inactive only' },
];
const paperTradableOptions = [
  { value: '', label: 'All paper-trading states' },
  { value: 'true', label: 'Paper-tradable only' },
  { value: 'false', label: 'Not paper-tradable' },
];
const orderingOptions = [
  { value: '', label: 'Default ordering' },
  { value: '-resolution_time', label: 'Resolution time · newest first' },
  { value: '-current_market_probability', label: 'Probability · highest first' },
  { value: '-liquidity', label: 'Liquidity · highest first' },
  { value: '-volume_24h', label: '24h volume · highest first' },
  { value: 'title', label: 'Title · A to Z' },
];

export function MarketsFilters({ filters, providers, events, onChange, onReset }: MarketsFiltersProps) {
  const categories = Array.from(new Set(events.map((event) => event.category))).sort((left, right) => left.localeCompare(right));

  function handleFieldChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.target;
    onChange({ ...filters, [name]: value });
  }

  return (
    <section className="panel markets-filters">
      <div className="markets-filters__header">
        <div>
          <p className="section-label">Filters</p>
          <h3>Refine the market catalog</h3>
          <p>Switch between demo and real read-only markets, then refine by provider, category, status, activity, or title.</p>
        </div>
        <div className="markets-filters__actions">
          <span className="muted-text">{providers.length} providers available</span>
          <button className="secondary-button" type="button" onClick={onReset}>
            Reset filters
          </button>
        </div>
      </div>

      <div className="markets-filters__grid">
        <label className="field-group">
          <span>Source</span>
          <select className="select-input" name="source_type" value={filters.source_type} onChange={handleFieldChange}>
            <option value="">All sources</option>
            <option value="demo">Demo markets</option>
            <option value="real_read_only">Real markets (read-only)</option>
          </select>
        </label>

        <label className="field-group">
          <span>Search</span>
          <input
            className="text-input"
            name="search"
            type="search"
            placeholder="Search by market title"
            value={filters.search}
            onChange={handleFieldChange}
          />
        </label>

        <label className="field-group">
          <span>Provider</span>
          <select className="select-input" name="provider" value={filters.provider} onChange={handleFieldChange}>
            <option value="">All providers</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.slug}>
                {provider.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Paper tradable</span>
          <select className="select-input" name="paper_tradable" value={filters.paper_tradable} onChange={handleFieldChange}>
            {paperTradableOptions.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Category</span>
          <select className="select-input" name="category" value={filters.category} onChange={handleFieldChange}>
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Status</span>
          <select className="select-input" name="status" value={filters.status} onChange={handleFieldChange}>
            {statusOptions.map((status) => (
              <option key={status || 'all'} value={status}>
                {status ? status[0].toUpperCase() + status.slice(1) : 'All statuses'}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Activity</span>
          <select className="select-input" name="is_active" value={filters.is_active} onChange={handleFieldChange}>
            {activeOptions.map((option) => (
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
