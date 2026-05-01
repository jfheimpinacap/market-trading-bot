import type { NavRoute } from '../types/system';

const currentYear = new Date().getFullYear();

type TopbarProps = {
  route?: NavRoute;
};

export function Topbar({ route }: TopbarProps) {
  return (
    <header className="topbar">
      <div className="topbar__context">
        <p className="topbar__title">{route?.label ?? 'Page not found'}</p>
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
