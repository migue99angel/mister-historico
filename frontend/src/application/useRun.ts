import { useQuery } from '@tanstack/react-query';

import { ApiError } from './apiError';
import { useGameApi } from './gameApi';
import type { RunViewDto } from './ports';
import { useRunTokenStore } from './runTokenStore';

/**
 * Cache key of one run's view. Every hook of the run (useRun, useTakeDecision,
 * useAdvanceBlock) reads and writes this entry; seed it after `startRun` to skip a fetch.
 */
export function runQueryKey(runId: string) {
  return ['runs', runId] as const;
}

/** Answers meaning this device's token no longer opens the run: 401, 403 or 404. */
const UNAVAILABLE_STATUSES: ReadonlySet<number | undefined> = new Set([401, 403, 404]);

/** True when the API will never accept this device's token for the run again. */
export function isRunUnavailableError(error: unknown): boolean {
  return error instanceof ApiError && UNAVAILABLE_STATUSES.has(error.status);
}

export type RunQueryState =
  /** No token on this device, or the API rejected it (401, 403 or 404); it was forgotten. */
  | { kind: 'unavailable' }
  | { kind: 'loading' }
  /** Any other failure (network, 5xx…); `retry` fetches the run again. */
  | { kind: 'error'; error: Error; retry: () => void }
  /** `isRefreshing` is true while a newer view is being fetched (e.g. after a 409). */
  | { kind: 'ready'; run: RunViewDto; isRefreshing: boolean };

/** Reads a run with the token this device keeps for it (see the RunTokenStore port). */
export function useRun(runId: string): RunQueryState {
  const gameApi = useGameApi();
  const runTokenStore = useRunTokenStore();
  const runToken = runTokenStore.read(runId);

  const query = useQuery({
    queryKey: runQueryKey(runId),
    queryFn: async () => {
      try {
        return await gameApi.getRun(runId, requireRunToken(runTokenStore.read(runId)));
      } catch (error) {
        if (isRunUnavailableError(error)) runTokenStore.remove(runId);
        throw error;
      }
    },
    enabled: runToken !== null,
  });

  if (runToken === null || isRunUnavailableError(query.error)) return { kind: 'unavailable' };
  if (query.data) return { kind: 'ready', run: query.data, isRefreshing: query.isFetching };
  if (query.error) {
    return {
      kind: 'error',
      error: query.error,
      retry: () => {
        void query.refetch();
      },
    };
  }
  return { kind: 'loading' };
}

/** The token as the API needs it; a missing one fails like the API would (401). */
export function requireRunToken(runToken: string | null): string {
  if (runToken === null) {
    throw new ApiError('problem', 'Esta partida no tiene token en este dispositivo.', {
      status: 401,
      code: 'run_token_required',
    });
  }
  return runToken;
}

export type RunCommandFailure =
  | { kind: 'conflict'; code: string | undefined }
  | { kind: 'unavailable' }
  | { kind: 'failed'; error: Error };

export interface RunCommand<Variables> {
  send: (variables: Variables) => Promise<RunViewDto | null>;
  isPending: boolean;
  failure: RunCommandFailure | null;
}
