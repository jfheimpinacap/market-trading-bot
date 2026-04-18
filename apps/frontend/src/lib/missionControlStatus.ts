import { ApiError } from '../services/api/client';

export type MissionControlStatusState =
  | { kind: 'empty'; message: string }
  | { kind: 'unavailable'; message: string };

function hasStatus(error: unknown, status: number) {
  return error instanceof ApiError && error.status == status;
}

export function resolveExpectedStatusError(
  error: unknown,
  config: {
    expected404Message: string;
    fallbackMessage: string;
    knownExpectedPhrases?: string[];
  },
): MissionControlStatusState {
  if (hasStatus(error, 404)) {
    return { kind: 'empty', message: config.expected404Message };
  }

  if (error instanceof Error) {
    const normalized = error.message.toLowerCase();
    const phrases = config.knownExpectedPhrases ?? [];
    if (phrases.some((phrase) => normalized.includes(phrase.toLowerCase()))) {
      return { kind: 'empty', message: config.expected404Message };
    }

    return { kind: 'unavailable', message: error.message || config.fallbackMessage };
  }

  return { kind: 'unavailable', message: config.fallbackMessage };
}

export function isSettledRejected(result: PromiseSettledResult<unknown>) {
  return result.status === 'rejected';
}
