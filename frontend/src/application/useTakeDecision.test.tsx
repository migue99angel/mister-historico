import type { QueryClient } from '@tanstack/react-query';
import { act, waitFor } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { describe, expect, it } from 'vitest';

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
});
