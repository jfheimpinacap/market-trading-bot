import type { NavRoute } from '../types/system';
import { NavItem } from './NavItem';

const sidebarFooterItems = ['Local-first', 'Personal use', 'Scaffold stage'];

type SidebarProps = {
  routes: NavRoute[];
  currentPath: string;
};

function isRouteActive(routePath: string, currentPath: string) {
  if (routePath === '/') {
    return currentPath === '/';
  }

  if (routePath.includes(':')) {
    const basePath = routePath.split('/:')[0];
    return currentPath.startsWith(`${basePath}/`);
  }

  return currentPath === routePath || currentPath.startsWith(`${routePath}/`);
}

export function Sidebar({ routes, currentPath }: SidebarProps) {
  const primaryRoutes = routes.filter((route) => !route.path.includes('/:'));

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <p className="section-label">Prediction Markets</p>
        <h2>market-trading-bot</h2>
        <p>Professional local workspace for research, guided automation, and manual paper trading.</p>
      </div>

      <nav className="sidebar__nav" aria-label="Primary navigation">
        {primaryRoutes.map((route) => (
          <NavItem key={route.path} label={route.label} path={route.path} active={isRouteActive(route.path, currentPath)} />
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
