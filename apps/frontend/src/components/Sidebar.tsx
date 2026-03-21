import type { NavRoute } from '../types/system';
import { NavItem } from './NavItem';

const sidebarFooterItems = ['Local-first', 'Personal use', 'Scaffold stage'];

type SidebarProps = {
  routes: NavRoute[];
  currentPath: string;
};

export function Sidebar({ routes, currentPath }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <p className="section-label">Prediction Markets</p>
        <h2>market-trading-bot</h2>
        <p>Professional local workspace for research, paper trading, and future automation.</p>
      </div>

      <nav className="sidebar__nav" aria-label="Primary navigation">
        {routes.map((route) => (
          <NavItem key={route.path} label={route.label} path={route.path} active={route.path === currentPath} />
        ))}
      </nav>

      <div className="sidebar__footer">
        {sidebarFooterItems.map((item) => (
          <span key={item} className="sidebar__tag">
            {item}
          </span>
        ))}
      </div>
    </aside>
  );
}
