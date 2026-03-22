import { SectionCard } from '../SectionCard';
import type { MarketRule } from '../../types/markets';
import { titleize } from './utils';

type MarketRulesCardProps = {
  shortRules: string;
  rules: MarketRule[];
};

export function MarketRulesCard({ shortRules, rules }: MarketRulesCardProps) {
  return (
    <SectionCard
      eyebrow="Rules"
      title="Resolution and rule guidance"
      description="Short-form rules plus any richer rule records returned by the backend detail endpoint."
    >
      <div className="market-rules">
        <div className="market-rules__summary">
          <h3>Short rules</h3>
          <p>{shortRules || 'No short rules were provided for this market.'}</p>
        </div>

        {rules.length > 0 ? (
          <ul className="market-rules__list">
            {rules.map((rule) => (
              <li key={rule.id} className="module-grid__item">
                <div>
                  <h3>{titleize(rule.source_type)}</h3>
                  <p>{rule.rule_text || 'No rule text provided.'}</p>
                </div>
                <p className="muted-text">{rule.resolution_criteria || 'No resolution criteria provided.'}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted-text">No extended rule records were returned for this market.</p>
        )}
      </div>
    </SectionCard>
  );
}
