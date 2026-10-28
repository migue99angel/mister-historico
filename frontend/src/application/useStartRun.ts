import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef } from 'react';

import { useGameApi } from './gameApi';
import type { RunViewDto } from './ports';
import { useRunTokenStore } from './runTokenStore';

/**
 * Query key of a run's `RunView`. `useStartRun` seeds it with the view `startRun` returns, so
 * the run screen can paint at once; `useRun` (T4.5) may reuse it or ignore it.
 */
export function runQueryKey(runId: string) {
  return ['runs', runId] as const;
}

export interface StartRunOptions {
  /** Called once the run exists and its token is stored, with the new run id. */
  onStarted?: (runId: string) => void;
}

export interface StartRun {
  /**
   * Starts a run of the season. Ignored while a start is in flight and once a run has
   * started, so each hook instance opens at most one run; a failed start can be retried.
   */
  start: (seasonId: string, options?: StartRunOptions) => void;
  isPending: boolean;
  /** The `ApiError` of the last failed start, cleared by the next start. */
  error: Error | null;
  /** Id of the run this hook started, once the API answers. */
  runId: string | null;
}

/** Starts a run, keeps its token in the RunTokenStore and seeds the run cache. */
export function useStartRun(): StartRun {
  const gameApi = useGameApi();
  const runTokenStore = useRunTokenStore();
  const queryClient = useQueryClient();
  // Set from the first start until it fails: two taps in the same frame both see
  // `isPending === false`, and a tap after success must not open a second run while the
  // screen navigates away.
  const locked = useRef(false);

  const { mutate, isPending, error, data } = useMutation({
    mutationFn: (seasonId: string) => gameApi.startRun({ seasonId }),
    onSuccess: ({ runToken, run }) => {
      runTokenStore.save(run.runId, runToken);
      queryClient.setQueryData<RunViewDto>(runQueryKey(run.runId), run);
    },
  });

  const start = useCallback(
    (seasonId: string, options: StartRunOptions = {}) => {
      if (locked.current) return;
      locked.current = true;
      mutate(seasonId, {
        onSuccess: ({ run }) => options.onStarted?.(run.runId),
        onError: () => {
          locked.current = false;
        },
      });
    },
    [mutate],
  );

  return { start, isPending, error, runId: data?.run.runId ?? null };
}
