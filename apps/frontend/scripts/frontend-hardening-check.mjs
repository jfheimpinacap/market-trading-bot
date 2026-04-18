import { readFile } from 'node:fs/promises';
import process from 'node:process';

async function main() {
  const cockpit = await readFile(new URL('../src/pages/CockpitPage.tsx', import.meta.url), 'utf8');
  const helper = await readFile(new URL('../src/lib/missionControlStatus.ts', import.meta.url), 'utf8');
  const css = await readFile(new URL('../src/styles/global.css', import.meta.url), 'utf8');

  const checks = [
    {
      id: 'trial-404-empty-state',
      ok: cockpit.includes("expected404Message: 'No trial run yet'"),
      fail: 'Missing 404->"No trial run yet" mapping for live-paper-trial-status.',
    },
    {
      id: 'smoke-404-empty-state',
      ok: cockpit.includes("expected404Message: 'No smoke test result yet'"),
      fail: 'Missing 404->"No smoke test result yet" mapping for live-paper-smoke-test-status.',
    },
    {
      id: '500-network-unavailable-state',
      ok: helper.includes("kind: 'unavailable'") && helper.includes('fallbackMessage'),
      fail: 'Expected unavailable/error path is not defined for non-404 failures.',
    },
    {
      id: 'advanced-dropdown-layering',
      ok:
        css.includes('.sidebar__advanced {') &&
        css.includes('z-index: 4;') &&
        css.includes('.sidebar__advanced .sidebar__nav {') &&
        css.includes('z-index: 5;') &&
        css.includes('.sidebar__footer {') &&
        css.includes('z-index: 1;'),
      fail: 'Sidebar layering hardening rules are missing for Advanced dropdown vs footer chips.',
    },
    {
      id: 'cockpit-no-global-block-on-secondary-cards',
      ok: cockpit.includes('Promise.allSettled([') && !cockpit.includes('await Promise.all([\n        getCockpitSummary()'),
      fail: 'Cockpit still uses strict Promise.all aggregate loading for primary/secondary cards.',
    },
  ];

  const failed = checks.filter((check) => !check.ok);
  if (failed.length > 0) {
    for (const check of failed) {
      console.error(`✗ ${check.id}: ${check.fail}`);
    }
    process.exit(1);
  }

  for (const check of checks) {
    console.log(`✓ ${check.id}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
