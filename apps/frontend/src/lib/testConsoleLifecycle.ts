import type { TestConsoleStatusResponse } from '../types/missionControl';

const TERMINAL_TEST_CONSOLE_STATUSES = new Set([
  'IDLE',
  'STOPPED',
  'COMPLETED',
  'COMPLETED_WITH_WARNINGS',
  'BLOCKED',
  'FAILED',
  'TIMED_OUT',
  'HUNG',
]);

export type TestConsoleLifecycleState = {
  normalizedStatus: string;
  runActive: boolean;
  hasLastCompletedRun: boolean;
  currentSnapshot: TestConsoleStatusResponse | null;
  effectiveLastCompletedSnapshot: TestConsoleStatusResponse | null;
};

export function resolveTestConsoleLifecycleState(
  currentStatus: TestConsoleStatusResponse | null,
  historicalSnapshot: TestConsoleStatusResponse | null,
): TestConsoleLifecycleState {
  const normalizedStatus = (currentStatus?.test_status ?? '').toUpperCase();
  const runActive = currentStatus?.has_active_run
    ?? (Boolean(currentStatus?.test_status) && !TERMINAL_TEST_CONSOLE_STATUSES.has(normalizedStatus));
  const hasLastCompletedRun = currentStatus?.has_last_completed_run
    ?? Boolean(
      !runActive
      && currentStatus?.ended_at
      && TERMINAL_TEST_CONSOLE_STATUSES.has(normalizedStatus),
    );

  return {
    normalizedStatus,
    runActive,
    hasLastCompletedRun,
    currentSnapshot: runActive ? currentStatus : null,
    effectiveLastCompletedSnapshot: hasLastCompletedRun
      ? (currentStatus ?? historicalSnapshot)
      : historicalSnapshot,
  };
}
