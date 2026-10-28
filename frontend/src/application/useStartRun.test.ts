import { act, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderHookWithRuntime,
} from '../../test/renderWithRuntime';
import { ApiError } from './apiError';
import type { RunViewDto } from './ports';
import { runQueryKey, useStartRun } from './useStartRun';

const problem = (status: number, code: string) =>
  HttpResponse.json(
    { type: 'about:blank', title: 'Failure', status, code },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

describe('useStartRun', () => {
  it('reports the id of the run it started', async () => {
    const onStarted = vi.fn<(runId: string) => void>();
    const { result } = renderHookWithRuntime(() => useStartRun());

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID, { onStarted });
    });

    await waitFor(() => {
      expect(result.current.runId).not.toBeNull();
    });
    expect(onStarted).toHaveBeenCalledExactlyOnceWith(result.current.runId);
  });

  it('keeps the run token so the run can be resumed', async () => {
    const { result, runTokenStore, gameApi } = renderHookWithRuntime(() => useStartRun());

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID);
    });
    await waitFor(() => {
      expect(result.current.runId).not.toBeNull();
    });

    const runId = result.current.runId ?? '';
    const token = runTokenStore.read(runId);
    expect(token).not.toBeNull();
    await expect(gameApi.getRun(runId, token ?? '')).resolves.toMatchObject({ runId });
  });

  it('seeds the run cache with the run view the API returned', async () => {
    const { result, queryClient } = renderHookWithRuntime(() => useStartRun());

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID);
    });
    await waitFor(() => {
      expect(result.current.runId).not.toBeNull();
    });

    const runId = result.current.runId ?? '';
    expect(queryClient.getQueryData<RunViewDto>(runQueryKey(runId))).toMatchObject({
      runId,
      seasonId: mockFixtures.TEST_SEASON_ID,
      status: 'in_progress',
    });
  });

  it('starts a single run when asked twice before the first one answers', async () => {
    const runtime = createTestRuntime();
    const startRun = vi.spyOn(runtime.gameApi, 'startRun');
    const onStarted = vi.fn<(runId: string) => void>();
    const { result } = renderHookWithRuntime(() => useStartRun(), { runtime });

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID, { onStarted });
      result.current.start(mockFixtures.TEST_SEASON_ID, { onStarted });
    });
    await waitFor(() => {
      expect(onStarted).toHaveBeenCalled();
    });

    expect(startRun).toHaveBeenCalledOnce();
    expect(onStarted).toHaveBeenCalledOnce();
  });

  it('exposes the ApiError when the run cannot start', async () => {
    mockServer.use(http.post('*/api/runs', () => problem(503, 'unavailable')));
    const { result } = renderHookWithRuntime(() => useStartRun());

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID);
    });

    await waitFor(() => {
      expect(result.current.error).toBeInstanceOf(ApiError);
    });
    expect(result.current.runId).toBeNull();
    expect(result.current.isPending).toBe(false);
  });

  it('lets the player retry after a failed start', async () => {
    mockServer.use(http.post('*/api/runs', () => problem(503, 'unavailable'), { once: true }));
    const onStarted = vi.fn<(runId: string) => void>();
    const { result } = renderHookWithRuntime(() => useStartRun());
    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID, { onStarted });
    });
    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });

    act(() => {
      result.current.start(mockFixtures.TEST_SEASON_ID, { onStarted });
    });

    await waitFor(() => {
      expect(onStarted).toHaveBeenCalledOnce();
    });
    expect(result.current.error).toBeNull();
  });
});
