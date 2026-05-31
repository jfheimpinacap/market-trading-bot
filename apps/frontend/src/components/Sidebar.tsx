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

type AdvancedRouteGroup = {
  label: string;
  hint: string;
  paths: string[];
};

const advancedRouteGroups: AdvancedRouteGroup[] = [
  {
    label: 'Mission Control / Tests',
    hint: 'Schedulers, operator flows, readiness and validation runs.',
    paths: [
      '/mission-control',
      '/automation',
      '/continuous-demo',
      '/runbooks',
      '/operator-queue',
      '/approvals',
      '/go-live',
      '/readiness',
      '/certification',
    ],
  },
  {
    label: 'Signals & Research',
    hint: 'Market scanning, narratives, opportunities and proposal intake.',
    paths: [
      '/scan-agent',
      '/signals',
      '/research',
      '/research-agent',
      '/opportunities',
      '/opportunity-cycle',
      '/proposals',
      '/agents',
      '/memory',
      '/learning',
    ],
  },
  {
    label: 'Prediction & Risk',
    hint: 'Prediction, risk, policy, safety and portfolio guardrails.',
    paths: [
      '/prediction',
      '/risk-agent',
      '/allocation',
      '/portfolio-governor',
      '/safety',
      '/policy-tuning',
      '/policy-rollout',
      '/automation-policy',
      '/trust-calibration',
      '/tuning',
    ],
  },
  {
    label: 'Execution / Paper Trading',
    hint: 'Paper execution, positions, venues and promotion/rollout surfaces.',
    paths: [
      '/execution',
      '/positions',
      '/semi-auto',
      '/real-ops',
      '/broker-bridge',
      '/execution-venue',
      '/venue-account',
      '/connectors',
      '/autonomous-trader',
      '/replay',
      '/experiments',
      '/champion-challenger',
      '/promotion',
      '/rollout',
      '/profile-manager',
    ],
  },
  {
    label: 'Diagnostics / Logs',
    hint: 'Traceability, incidents, notifications, postmortems and system evidence.',
    paths: [
      '/trace',
      '/alerts',
      '/notifications',
      '/incidents',
      '/chaos',
      '/evaluation',
      '/postmortem',
      '/postmortem-board',
      '/runtime',
      '/system',
    ],
  },
  {
    label: 'System / Settings',
    hint: 'Autonomy governance, lifecycle boards and local settings.',
    paths: [
      '/settings',
      '/autonomy',
      '/autonomy-rollout',
      '/autonomy-roadmap',
      '/autonomy-scenarios',
      '/autonomy-campaigns',
      '/autonomy-program',
      '/autonomy-scheduler',
      '/autonomy-launch',
      '/autonomy-activation',
      '/autonomy-operations',
      '/autonomy-interventions',
      '/autonomy-recovery',
      '/autonomy-disposition',
      '/autonomy-closeout',
      '/autonomy-followup',
      '/autonomy-feedback',
      '/autonomy-insights',
      '/autonomy-advisory',
      '/autonomy-advisory-resolution',
      '/autonomy-backlog',
      '/autonomy-intake',
      '/autonomy-planning-review',
      '/autonomy-seed-review',
      '/autonomy-seed',
      '/autonomy-package',
      '/autonomy-package-review',
      '/autonomy-decision',
    ],
  },
];

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

function groupAdvancedRoutes(routes: NavRoute[]) {
  const routeByPath = new Map(routes.map((route) => [getBasePath(route.path), route]));
  const assignedPaths = new Set<string>();

  const groupedRoutes = advancedRouteGroups.map((group) => {
    const items = group.paths
      .map((path) => routeByPath.get(path))
      .filter((route): route is NavRoute => Boolean(route));

    items.forEach((route) => assignedPaths.add(getBasePath(route.path)));

    return { ...group, routes: items };
  });

  const fallbackRoutes = routes
    .filter((route) => !assignedPaths.has(getBasePath(route.path)))
    .sort((a, b) => a.label.localeCompare(b.label));

  if (fallbackRoutes.length > 0) {
    groupedRoutes.push({
      label: 'Diagnostics / System overflow',
      hint: 'Uncategorized advanced routes kept visible without changing paths.',
      paths: [],
      routes: fallbackRoutes,
    });
  }

  return groupedRoutes.filter((group) => group.routes.length > 0);
}

export function Sidebar({ routes, currentPath }: SidebarProps) {
  const primaryPathSet = new Set<string>(primaryPathOrder);

  const primaryRoutes = primaryPathOrder
    .map((path) => routes.find((route) => route.path === path))
    .filter((route): route is NavRoute => Boolean(route));

  const advancedRoutes = routes
    .filter((route) => !route.path.includes('/:'))
    .filter((route) => !primaryPathSet.has(route.path));

  const advancedGroups = groupAdvancedRoutes(advancedRoutes);
  const isAdvancedActive = advancedRoutes.some((route) => isRouteActive(route.path, currentPath));
  const showAdvanced = isAdvancedActive || !primaryRoutes.some((route) => isRouteActive(route.path, currentPath));

  return (
    <aside className="sidebar">
      <div className="sidebar__brand sidebar__header">
        <p className="section-label">Prediction Markets</p>
        <h2>market-trading-bot</h2>
      </div>

      <div className="sidebar__scroll" aria-label="Sidebar navigation area">
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
          <div className="sidebar__advanced-groups">
            {advancedGroups.map((group) => {
              const isGroupActive = group.routes.some((route) => isRouteActive(route.path, currentPath));
              return (
                <details key={group.label} className="sidebar__advanced-group" open={showAdvanced && isGroupActive}>
                  <summary title={group.hint}>
                    <span>{group.label}</span>
                    <small>{group.routes.length}</small>
                  </summary>
                  <nav className="sidebar__nav sidebar__nav--nested" aria-label={`${group.label} navigation`}>
                    {group.routes.map((route) => (
                      <NavItem key={route.path} label={route.label} path={getBasePath(route.path)} active={isRouteActive(route.path, currentPath)} />
                    ))}
                  </nav>
                </details>
              );
            })}
          </div>
        </details>
      </div>

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
