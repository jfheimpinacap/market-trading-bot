import type { NavRoute } from '../types/system';
import { SYSTEM_VERSION_LABEL } from '../lib/config';
import { NavItem } from './NavItem';

const sidebarFooterItems = ['Local-first', 'Personal use', 'Scaffold stage'];

const primaryPathOrder = ['/', '/markets', '/portfolio', '/cockpit'] as const;

const primaryLabelOverrides: Record<string, string> = {
  '/cockpit': 'Advanced / Cockpit',
};

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

function getBasePath(path: string) {
  return path.includes('/:') ? path.split('/:')[0] : path;
}

export function Sidebar({ routes, currentPath }: SidebarProps) {
  const primaryPathSet = new Set<string>(primaryPathOrder);

  const primaryRoutes = primaryPathOrder
    .map((path) => routes.find((route) => route.path === path))
    .filter((route): route is NavRoute => Boolean(route));

  const advancedRoutes = routes
    .filter((route) => !route.path.includes('/:'))
    .filter((route) => !primaryPathSet.has(route.path))
    .sort((a, b) => a.label.localeCompare(b.label));

  const isAdvancedActive = advancedRoutes.some((route) => isRouteActive(route.path, currentPath));
  const showAdvanced = isAdvancedActive || !primaryRoutes.some((route) => isRouteActive(route.path, currentPath));

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <p className="section-label">Prediction Markets</p>
        <h2>market-trading-bot</h2>
      </div>

      <div className="sidebar__section">
        <p className="sidebar__section-label">Principal</p>
        <nav className="sidebar__nav" aria-label="Primary navigation">
          {primaryRoutes.map((route) => (
            <NavItem
              key={route.path}
              label={primaryLabelOverrides[route.path] ?? route.label}
              path={route.path}
              active={isRouteActive(route.path, currentPath)}
            />
          ))}
        </nav>
      </div>

      <details className="sidebar__advanced" open={showAdvanced}>
        <summary>
          <span>Advanced</span>
          <small>{advancedRoutes.length} routes</small>
        </summary>
        <p className="sidebar__advanced-hint">Technical controls, diagnostics, governance, and operator tooling.</p>
        <nav className="sidebar__nav" aria-label="Advanced navigation">
          {advancedRoutes.map((route) => (
            <NavItem key={route.path} label={route.label} path={getBasePath(route.path)} active={isRouteActive(route.path, currentPath)} />
          ))}
        </nav>
      </details>

      <div className="sidebar__footer">
        {sidebarFooterItems.map((item) => (
          <span key={item} className="sidebar__tag">
            {item}
          </span>
        ))}
        <div className="sidebar__version">
          <p>Version</p>
          <strong>{SYSTEM_VERSION_LABEL}</strong>
        </div>
      </div>
    </aside>
  );
}
