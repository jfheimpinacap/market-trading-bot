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
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Solo activos' },
  { value: 'false', label: 'Solo inactivos' },
];
const paperTradableOptions = [
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Aptos para paper' },
  { value: 'false', label: 'No aptos para paper' },
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
          <h3>Filtrar mercados</h3>
          <p>Usa pocos filtros para encontrar rápido lo que buscas. Si no ves resultados, prueba limpiar filtros.</p>
        </div>
        <div className="markets-filters__actions">
          <span className="muted-text">{providers.length} proveedores disponibles</span>
          <button className="secondary-button" type="button" onClick={onReset}>
            Restablecer
          </button>
        </div>
      </div>

      <div className="markets-filters__grid">
        <label className="field-group">
          <span>Fuente</span>
          <select className="select-input" name="source_type" value={filters.source_type} onChange={handleFieldChange}>
            <option value="">Todas</option>
            <option value="demo">Mercados demo</option>
            <option value="real_read_only">Mercados reales (solo lectura)</option>
          </select>
        </label>

        <label className="field-group">
          <span>Búsqueda</span>
          <input
            className="text-input"
            name="search"
            type="search"
            placeholder="Buscar por nombre del mercado"
            value={filters.search}
            onChange={handleFieldChange}
          />
        </label>

        <label className="field-group">
          <span>Proveedor</span>
          <select className="select-input" name="provider" value={filters.provider} onChange={handleFieldChange}>
            <option value="">Todos</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.slug}>
                {provider.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Operable en paper</span>
          <select className="select-input" name="paper_tradable" value={filters.paper_tradable} onChange={handleFieldChange}>
            {paperTradableOptions.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Categoría</span>
          <select className="select-input" name="category" value={filters.category} onChange={handleFieldChange}>
            <option value="">Todas</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Estado</span>
          <select className="select-input" name="status" value={filters.status} onChange={handleFieldChange}>
            {statusOptions.map((status) => (
              <option key={status || 'all'} value={status}>
                {status ? status[0].toUpperCase() + status.slice(1) : 'Todos'}
              </option>
            ))}
          </select>
        </label>

        <label className="field-group">
          <span>Actividad</span>
          <select className="select-input" name="is_active" value={filters.is_active} onChange={handleFieldChange}>
            {activeOptions.map((option) => (
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
