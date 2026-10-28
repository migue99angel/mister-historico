import { waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { describe, expect, it } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderHookWithRuntime,
} from '../../test/renderWithRuntime';
import { runQueryKey, useRun } from './useRun';

const UNKNOWN_RUN_ID = '00000000-0000-4000-8000-000000000000';

async function runtimeWithStartedRun() {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  runtime.runTokenStore.save(started.run.runId, started.runToken);
  return { runtime, runId: started.run.runId, runToken: started.runToken };
}

describe('runQueryKey', () => {
  it('identifies the cache entry of one run, shared by every hook of that run', () => {
    expect(runQueryKey('run-1')).toEqual(runQueryKey('run-1'));
    expect(runQueryKey('run-1')).not.toEqual(runQueryKey('run-2'));
  });
});

describe('useRun', () => {
  it('loads the run view with the token stored on this device', async () => {
    const { runtime, runId } = await runtimeWithStartedRun();

    const { result } = renderHookWithRuntime(() => useRun(runId), { runtime });

    expect(result.current.kind).toBe('loading');
    await waitFor(() => {
      expect(result.current.kind).toBe('ready');
    });
    expect(result.current.kind === 'ready' && result.current.run.runId).toBe(runId);
  });

  it('caches the run view under runQueryKey', async () => {
    const { runtime, runId } = await runtimeWithStartedRun();

    const { result } = renderHookWithRuntime(() => useRun(runId), { runtime });

    await waitFor(() => {
      expect(result.current.kind).toBe('ready');
    });
    expect(runtime.queryClient.getQueryData(runQueryKey(runId))).toMatchObject({ runId });
  });

  it('is unavailable without calling the API when this device has no token for the run', () => {
    const requests: string[] = [];
    mockServer.use(
      http.get('*/api/runs/:runId', ({ request }) => {
        requests.push(request.url);
      }),
    );

    const { result } = renderHookWithRuntime(() => useRun(UNKNOWN_RUN_ID));

    expect(result.current.kind).toBe('unavailable');
    expect(requests).toEqual([]);
  });

  it('forgets the token and is unavailable when the API rejects it with 403', async () => {
    const { runtime, runId } = await runtimeWithStartedRun();
    runtime.runTokenStore.save(runId, 'a-token-from-another-run');

    const { result } = renderHookWithRuntime(() => useRun(runId), { runtime });

    await waitFor(() => {
      expect(result.current.kind).toBe('unavailable');
    });
    expect(runtime.runTokenStore.read(runId)).toBeNull();
  });

  it('forgets the token and is unavailable when the API no longer knows the run (404)', async () => {
    const runtime = createTestRuntime();
    runtime.runTokenStore.save(UNKNOWN_RUN_ID, 'a-token');

    const { result } = renderHookWithRuntime(() => useRun(UNKNOWN_RUN_ID), { runtime });

    await waitFor(() => {
      expect(result.current.kind).toBe('unavailable');
    });
    expect(runtime.runTokenStore.read(UNKNOWN_RUN_ID)).toBeNull();
  });

  it('forgets the token and is unavailable when the API asks for credentials (401)', async () => {
    const { runtime, runId } = await runtimeWithStartedRun();
    mockServer.use(
      http.get('*/api/runs/:runId', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Run token required', status: 401 },
          { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );

    const { result } = renderHookWithRuntime(() => useRun(runId), { runtime });

    await waitFor(() => {
      expect(result.current.kind).toBe('unavailable');
    });
    expect(runtime.runTokenStore.read(runId)).toBeNull();
  });

  it('keeps the token and reports an error the player can retry when the API fails', async () => {
    const { runtime, runId, runToken } = await runtimeWithStartedRun();
    mockServer.use(
      http.get('*/api/runs/:runId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );

    const { result } = renderHookWithRuntime(() => useRun(runId), { runtime });

    await waitFor(() => {
      expect(result.current.kind).toBe('error');
    });
    expect(runtime.runTokenStore.read(runId)).toBe(runToken);

    if (result.current.kind === 'error') result.current.retry();

    await waitFor(() => {
      expect(result.current.kind).toBe('ready');
    });
  });
});
