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
import { useAdvanceBlock } from './useAdvanceBlock';

/** Records the Idempotency-Key of every advance request; the original handler answers. */
function spyOnAdvances(): (string | null)[] {
  const keys: (string | null)[] = [];
  mockServer.use(
    http.post('*/api/runs/:runId/advance', ({ request }) => {
      keys.push(request.headers.get('Idempotency-Key'));
    }),
  );
  return keys;
}

/** A run whose first block has every dilemma decided, ready to be simulated. */
async function renderRunReadyToAdvance() {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  const runId = started.run.runId;
  const runToken = started.runToken;
  let version = 0;
  for (const [dilemmaId, optionId] of [
    ['board-meeting', 'support-the-board'],
    ['summer-striker', 'sign-the-veteran'],
  ] as const) {
    const view = await runtime.gameApi.takeDecision({
      runId,
      runToken,
      idempotencyKey: `seed-${dilemmaId}`,
      dilemmaId,
      optionId,
      expectedVersion: version,
    });
    version = view.version;
  }
  runtime.runTokenStore.save(runId, runToken);
  const rendered = renderHookWithRuntime(
    () => ({ run: useRun(runId), advance: useAdvanceBlock(runId) }),
    { runtime },
  );
  await waitFor(() => {
    expect(rendered.result.current.run.kind).toBe('ready');
  });
  return { ...rendered, runId };
}

function cachedRun(queryClient: QueryClient, runId: string) {
  const run = queryClient.getQueryData<RunViewDto>(runQueryKey(runId));
  if (!run) throw new Error('The run is not cached.');
  return run;
}

describe('useAdvanceBlock', () => {
  it('stores the simulated block: its summary and the next block', async () => {
    const { result, queryClient, runId } = await renderRunReadyToAdvance();

    await act(async () => {
      await result.current.advance.send();
    });

    const run = cachedRun(queryClient, runId);
    expect(run.lastBlockSummary?.blockNumber).toBe(1);
    expect(run.block.number).toBe(2);
  });

  it('simulates a double tap only once', async () => {
    const keys = spyOnAdvances();
    const { result } = await renderRunReadyToAdvance();

    await act(async () => {
      await Promise.all([result.current.advance.send(), result.current.advance.send()]);
    });

    expect(keys).toHaveLength(1);
  });

  it('retries a simulation lost to the network with the same Idempotency-Key', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/advance', () => HttpResponse.error(), { once: true }),
    );
    const keys = spyOnAdvances();
    const { result, queryClient, runId } = await renderRunReadyToAdvance();

    await act(async () => {
      await result.current.advance.send();
    });
    expect(result.current.advance.failure?.kind).toBe('failed');
    await act(async () => {
      await result.current.advance.send();
    });

    expect(keys).toHaveLength(2);
    expect(keys[1]).toBe(keys[0]);
    expect(cachedRun(queryClient, runId).block.number).toBe(2);
  });

  it('reports a conflict when the API refuses to simulate (409)', async () => {
    mockServer.use(
      http.post(
        '*/api/runs/:runId/advance',
        () =>
          HttpResponse.json(
            {
              type: 'about:blank',
              title: 'Run already finished',
              status: 409,
              code: 'run_already_finished',
            },
            { status: 409, headers: { 'Content-Type': 'application/problem+json' } },
          ),
        { once: true },
      ),
    );
    const { result } = await renderRunReadyToAdvance();

    await act(async () => {
      await result.current.advance.send();
    });

    expect(result.current.advance.failure).toEqual({
      kind: 'conflict',
      code: 'run_already_finished',
    });
  });
});
