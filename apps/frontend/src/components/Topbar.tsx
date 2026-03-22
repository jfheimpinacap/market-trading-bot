import type { NavRoute } from '../types/system';

const currentYear = new Date().getFullYear();

type TopbarProps = {
  route?: NavRoute;
};

export function Topbar({ route }: TopbarProps) {
  return (
    <header className="topbar">
      <div>
        <p className="section-label">Current section</p>
        <h1>{route?.label ?? 'Page not found'}</h1>
        <p className="topbar__description">
          {route?.description ?? 'The requested route does not exist in the current frontend scaffold.'}
        </p>
      </div>
      <div className="topbar__meta">
        <span>Local environment</span>
        <span>Markets module ready · {currentYear}</span>
      </div>
    </header>
  );
}
