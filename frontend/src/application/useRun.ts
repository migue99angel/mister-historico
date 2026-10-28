import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';

import { ApiError } from './apiError';
import { useGameApi } from './gameApi';
import type { GameApi, IdempotentRunCommand, RunViewDto } from './ports';
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
    // Only this run's commands change it, and they write their reply to this entry; a 409
    // invalidates it. So a cached view (e.g. seeded after startRun) never needs a refetch.
    staleTime: Infinity,
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

// Commands on a run (decide a dilemma, simulate a block) share this plumbing: they send the
// version of the cached view, keep one Idempotency-Key per attempt and write the reply back to
// the run's cache entry.

export type RunCommandFailure =
  /** 409 (`version_conflict`, `dilemma_already_decided`, `run_already_finished`…): reloaded. */
  | { kind: 'conflict'; code: string | undefined }
  /** The token no longer opens the run (401, 403 or 404); useRun turns unavailable. */
  | { kind: 'unavailable' }
  /** Any other 4xx (e.g. 422 `invalid_option`): the attempt is dropped and the run reloaded. */
  | { kind: 'rejected'; code: string | undefined }
  /** Network, 5xx or 429: sending the same variables again retries the same attempt. */
  | { kind: 'failed'; error: Error };

export interface RunCommand<Variables> {
  /**
   * Sends the command against the cached view's version. Sending the variables of the last
   * failed attempt again reuses its Idempotency-Key, so a retry never applies twice. Ignored
   * (resolves `null`) while another attempt is in flight, while the run view is being
   * (re)loaded, so a stale version is never sent, or before the run has loaded.
   * Resolves with the new run view, or `null` when ignored or failed (see `failure`).
   */
  send: (variables: Variables) => Promise<RunViewDto | null>;
  isPending: boolean;
  /** Why the last attempt failed; cleared when a new attempt starts. */
  failure: RunCommandFailure | null;
}

export type RunCommandRequest = IdempotentRunCommand & { expectedVersion: number };

export type RunCommandExecutor<Variables> = (
  gameApi: GameApi,
  request: RunCommandRequest,
  variables: Variables,
) => Promise<RunViewDto>;

interface Attempt<Variables> {
  variables: Variables;
  fingerprint: string;
  expectedVersion: number;
  idempotencyKey: string;
}

function nextAttempt<Variables>(
  failed: Attempt<Variables> | null,
  variables: Variables,
  version: number,
): Attempt<Variables> {
  const fingerprint = JSON.stringify([variables]);
  if (failed?.fingerprint === fingerprint) return failed;
  return { variables, fingerprint, expectedVersion: version, idempotencyKey: crypto.randomUUID() };
}

/** Only these may succeed when resent unchanged: no answer, a server error or a rate limit. */
function isRetryable(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status === undefined) return true;
  return error.status === 429 || error.status >= 500 || error.status < 400;
}

function toFailure(error: unknown): RunCommandFailure {
  if (isRetryable(error)) {
    return { kind: 'failed', error: error instanceof Error ? error : new Error(String(error)) };
  }
  if (isRunUnavailableError(error)) return { kind: 'unavailable' };
  const { status, code } = error as ApiError;
  return status === 409 ? { kind: 'conflict', code } : { kind: 'rejected', code };
}

/** Shared by useTakeDecision and useAdvanceBlock; see RunCommand. */
export function useRunCommand<Variables>(
  runId: string,
  execute: RunCommandExecutor<Variables>,
): RunCommand<Variables> {
  const gameApi = useGameApi();
  const runTokenStore = useRunTokenStore();
  const queryClient = useQueryClient();
  // Refs, not state: a double tap fires twice before React re-renders.
  const inFlight = useRef(false);
  const failedAttempt = useRef<Attempt<Variables> | null>(null);
  const [failure, setFailure] = useState<RunCommandFailure | null>(null);

  const { mutateAsync, isPending } = useMutation({
    mutationFn: async (attempt: Attempt<Variables>) =>
      execute(
        gameApi,
        {
          runId,
          runToken: requireRunToken(runTokenStore.read(runId)),
          idempotencyKey: attempt.idempotencyKey,
          expectedVersion: attempt.expectedVersion,
        },
        attempt.variables,
      ),
  });

  const send = useCallback(
    async (variables: Variables): Promise<RunViewDto | null> => {
      const queryKey = runQueryKey(runId);
      const current = queryClient.getQueryData<RunViewDto>(queryKey);
      if (inFlight.current || !current || queryClient.isFetching({ queryKey }) > 0) return null;
      inFlight.current = true;
      setFailure(null);
      let attempt: Attempt<Variables> | null = null;
      try {
        // Inside the try: crypto.randomUUID throws outside a secure context.
        attempt = nextAttempt(failedAttempt.current, variables, current.version);
        const run = await mutateAsync(attempt);
        failedAttempt.current = null;
        // A reload started before this reply would overwrite it with an older view.
        await queryClient.cancelQueries({ queryKey });
        queryClient.setQueryData(queryKey, run);
        return run;
      } catch (error) {
        const reason = toFailure(error);
        failedAttempt.current = reason.kind === 'failed' ? attempt : null;
        setFailure(reason);
        if (reason.kind !== 'failed') {
          void queryClient.invalidateQueries({ queryKey });
        }
        return null;
      } finally {
        inFlight.current = false;
      }
    },
    [mutateAsync, queryClient, runId],
  );

  return { send, isPending, failure };
}
