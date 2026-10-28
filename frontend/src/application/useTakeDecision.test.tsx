import type { QueryClient } from '@tanstack/react-query';
import { act, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderHookWithRuntime,
} from '../../test/renderWithRuntime';
import type { RunViewDto } from './ports';
import { runQueryKey, useRun } from './useRun';
import { useTakeDecision } from './useTakeDecision';

const BOARD_MEETING = { dilemmaId: 'board-meeting', optionId: 'support-the-board' };

interface SentDecision {
  idempotencyKey: string | null;
  body: unknown;
}

/** Records every decision request and lets the original handler answer it. */
function spyOnDecisions(): SentDecision[] {
  const sent: SentDecision[] = [];
  mockServer.use(
    http.post('*/api/runs/:runId/decisions', async ({ request }) => {
      sent.push({
        idempotencyKey: request.headers.get('Idempotency-Key'),
        body: await request.clone().json(),
      });
    }),
  );
  return sent;
}

async function renderLoadedRun() {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  const runId = started.run.runId;
  runtime.runTokenStore.save(runId, started.runToken);
  const rendered = renderHookWithRuntime(
    () => ({ run: useRun(runId), decision: useTakeDecision(runId) }),
    { runtime },
  );
  await waitFor(() => {
    expect(rendered.result.current.run.kind).toBe('ready');
  });
  return { ...rendered, runId, runToken: started.runToken };
}

function cachedRun(queryClient: QueryClient, runId: string) {
  const run = queryClient.getQueryData<RunViewDto>(runQueryKey(runId));
  if (!run) throw new Error('The run is not cached.');
  return run;
}

describe('useTakeDecision', () => {
  it('stores the run view the API returns, without the decided dilemma', async () => {
    const { result, queryClient, runId } = await renderLoadedRun();

    let returned: RunViewDto | null = null;
    await act(async () => {
      returned = await result.current.decision.send(BOARD_MEETING);
    });

    const run = cachedRun(queryClient, runId);
    expect(returned).toEqual(run);
    expect(run.pendingDilemmas.map((dilemma) => dilemma.id)).toEqual(['summer-striker']);
    expect(result.current.decision.failure).toBeNull();
  });

  it('sends the version of the current view and an Idempotency-Key the API accepts', async () => {
    const sent = spyOnDecisions();
    const { result } = await renderLoadedRun();

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });

    expect(sent).toHaveLength(1);
    expect(sent[0]?.body).toEqual({ ...BOARD_MEETING, expectedVersion: 0 });
    expect(sent[0]?.idempotencyKey?.length).toBeGreaterThanOrEqual(8);
    expect(sent[0]?.idempotencyKey?.length).toBeLessThanOrEqual(128);
  });

  it('sends a double tap only once', async () => {
    const sent = spyOnDecisions();
    const { result } = await renderLoadedRun();

    await act(async () => {
      const first = result.current.decision.send(BOARD_MEETING);
      const second = result.current.decision.send(BOARD_MEETING);
      await Promise.all([first, second]);
    });

    expect(sent).toHaveLength(1);
  });

  it('reports pending while the decision is in flight', async () => {
    const { result } = await renderLoadedRun();

    let sending: Promise<unknown> = Promise.resolve();
    act(() => {
      sending = result.current.decision.send(BOARD_MEETING);
    });

    await waitFor(() => {
      expect(result.current.decision.isPending).toBe(true);
    });
    await act(async () => {
      await sending;
    });
    expect(result.current.decision.isPending).toBe(false);
  });

  it('retries a decision lost to the network with the same Idempotency-Key', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => HttpResponse.error(), { once: true }),
    );
    const sent = spyOnDecisions();
    const { result, queryClient, runId } = await renderLoadedRun();

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });
    expect(result.current.decision.failure?.kind).toBe('failed');

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });

    expect(sent).toHaveLength(2);
    expect(sent[1]?.idempotencyKey).toBe(sent[0]?.idempotencyKey);
    expect(sent[1]?.body).toEqual(sent[0]?.body);
    expect(result.current.decision.failure).toBeNull();
    expect(cachedRun(queryClient, runId).decisions).toHaveLength(1);
  });

  it('starts a new attempt with a new Idempotency-Key when the player changes the option', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => HttpResponse.error(), { once: true }),
    );
    const sent = spyOnDecisions();
    const { result } = await renderLoadedRun();

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });
    await act(async () => {
      await result.current.decision.send({ ...BOARD_MEETING, optionId: 'confront-the-board' });
    });

    expect(sent).toHaveLength(2);
    expect(sent[1]?.idempotencyKey).not.toBe(sent[0]?.idempotencyKey);
  });

  it('reports a conflict and reloads the run when the API answers 409', async () => {
    const { result, gameApi, queryClient, runId, runToken } = await renderLoadedRun();
    // Another tab decides first: this view's version is now stale.
    await gameApi.takeDecision({
      runId,
      runToken,
      idempotencyKey: 'another-tab-attempt',
      ...BOARD_MEETING,
      expectedVersion: 0,
    });

    await act(async () => {
      await result.current.decision.send({
        dilemmaId: 'summer-striker',
        optionId: 'sign-the-veteran',
      });
    });

    expect(result.current.decision.failure).toEqual({
      kind: 'conflict',
      code: 'version_conflict',
    });
    await waitFor(() => {
      expect(cachedRun(queryClient, runId).version).toBe(1);
    });
  });

  it('reports the run as unavailable when the API rejects the token', async () => {
    const { result, runTokenStore, runId } = await renderLoadedRun();
    runTokenStore.save(runId, 'a-token-from-another-run');

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });

    expect(result.current.decision.failure).toEqual({ kind: 'unavailable' });
  });

  it('ignores a decision before the run view has loaded', async () => {
    const sent = spyOnDecisions();
    const { result } = renderHookWithRuntime(() => useTakeDecision('not-loaded'));

    let returned: RunViewDto | null = null;
    await act(async () => {
      returned = await result.current.send(BOARD_MEETING);
    });

    expect(returned).toBeNull();
    expect(sent).toEqual([]);
  });

  it('ignores a decision while the run view is being reloaded, so it never sends a stale version', async () => {
    const { result, queryClient, runId } = await renderLoadedRun();
    const sent = spyOnDecisions();
    let releaseGet: () => void = () => undefined;
    const getHeld = new Promise<void>((resolve) => {
      releaseGet = resolve;
    });
    mockServer.use(
      http.get('*/api/runs/:runId', async () => {
        await getHeld;
      }),
    );
    void queryClient.refetchQueries({ queryKey: runQueryKey(runId) });
    await waitFor(() => {
      expect(queryClient.isFetching({ queryKey: runQueryKey(runId) })).toBe(1);
    });

    let returned: RunViewDto | null = cachedRun(queryClient, runId);
    await act(async () => {
      returned = await result.current.decision.send(BOARD_MEETING);
    });

    expect(returned).toBeNull();
    expect(sent).toEqual([]);
    releaseGet();
  });

  it('keeps the reply of a decision over an older reload that answers after it', async () => {
    const { result, queryClient, runId } = await renderLoadedRun();
    const staleView = cachedRun(queryClient, runId);
    let releaseGet: () => void = () => undefined;
    const getHeld = new Promise<void>((resolve) => {
      releaseGet = resolve;
    });
    mockServer.use(
      http.get('*/api/runs/:runId', async () => {
        await getHeld;
        return HttpResponse.json(staleView);
      }),
    );

    await act(async () => {
      const sending = result.current.decision.send(BOARD_MEETING);
      void queryClient.refetchQueries({ queryKey: runQueryKey(runId) });
      await sending;
    });
    releaseGet();
    await act(() => new Promise((resolve) => setTimeout(resolve, 20)));

    expect(cachedRun(queryClient, runId).version).toBe(1);
  });

  it.each([500, 503, 429])(
    'retries a decision the API failed with %i with the same Idempotency-Key',
    async (status) => {
      mockServer.use(
        http.post(
          '*/api/runs/:runId/decisions',
          () =>
            HttpResponse.json(
              { type: 'about:blank', title: 'Unavailable', status },
              { status, headers: { 'Content-Type': 'application/problem+json' } },
            ),
          { once: true },
        ),
      );
      const sent = spyOnDecisions();
      const { result } = await renderLoadedRun();

      await act(async () => {
        await result.current.decision.send(BOARD_MEETING);
      });
      expect(result.current.decision.failure?.kind).toBe('failed');
      await act(async () => {
        await result.current.decision.send(BOARD_MEETING);
      });

      expect(sent[1]?.idempotencyKey).toBe(sent[0]?.idempotencyKey);
    },
  );

  it('drops a decision the API rejects with another 4xx instead of retrying it with the same key', async () => {
    mockServer.use(
      http.post(
        '*/api/runs/:runId/decisions',
        () =>
          HttpResponse.json(
            {
              type: 'about:blank',
              title: 'Invalid option',
              status: 422,
              code: 'invalid_option',
            },
            { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
          ),
        { once: true },
      ),
    );
    const sent = spyOnDecisions();
    const { result } = await renderLoadedRun();

    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });
    expect(result.current.decision.failure).toEqual({ kind: 'rejected', code: 'invalid_option' });
    await act(async () => {
      await result.current.decision.send(BOARD_MEETING);
    });

    expect(sent).toHaveLength(2);
    expect(sent[1]?.idempotencyKey).not.toBe(sent[0]?.idempotencyKey);
  });

  it('reports a failure instead of throwing when no Idempotency-Key can be generated', async () => {
    const { result } = await renderLoadedRun();
    const randomUUID = vi.spyOn(crypto, 'randomUUID').mockImplementationOnce(() => {
      throw new Error('crypto.randomUUID needs a secure context');
    });

    let returned: RunViewDto | null | undefined;
    await act(async () => {
      returned = await result.current.decision.send(BOARD_MEETING);
    });
    randomUUID.mockRestore();

    expect(returned).toBeNull();
    expect(result.current.decision.failure?.kind).toBe('failed');
  });

  it('accepts a new decision after one that could not generate its Idempotency-Key', async () => {
    const { result } = await renderLoadedRun();
    const randomUUID = vi.spyOn(crypto, 'randomUUID').mockImplementationOnce(() => {
      throw new Error('crypto.randomUUID needs a secure context');
    });
    await act(async () => {
      await result.current.decision.send(BOARD_MEETING).catch(() => null);
    });
    randomUUID.mockRestore();

    let returned: RunViewDto | null = null;
    await act(async () => {
      returned = await result.current.decision.send(BOARD_MEETING);
    });

    expect(returned).not.toBeNull();
  });
});
