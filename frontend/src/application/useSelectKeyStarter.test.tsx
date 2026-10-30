import { act } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { expect, it } from 'vitest';
import { createTestRuntime, mockFixtures, mockServer, renderHookWithRuntime } from '../../test/renderWithRuntime';
import { runQueryKey } from './useRun';
import { useSelectKeyStarter } from './useSelectKeyStarter';

it.each([false, true])('sends an authenticated selection once and retries a lost reply (%s) with the same key', async (loseReply) => {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  const { runId } = started.run;
  runtime.runTokenStore.save(runId, started.runToken);
  runtime.queryClient.setQueryData(runQueryKey(runId), started.run);
  const requests: Request[] = [];
  mockServer.use(http.post('*/api/runs/:runId/key-starter', ({ request }) => {
    requests.push(request.clone());
    return loseReply && requests.length === 1 ? HttpResponse.error() : HttpResponse.json({ ...started.run, version: 1 });
  }));
  const { result } = renderHookWithRuntime(() => useSelectKeyStarter(runId), { runtime });
  const choice = { fixtureId: 'test-fixture', playerId: 'test-player' };
  await act(async () => { await Promise.all([result.current.send(choice), result.current.send(choice)]); });
  expect(requests).toHaveLength(1);
  if (loseReply) {
    expect(result.current.failure?.kind).toBe('failed');
    await act(async () => { await result.current.send(choice); });
    expect(requests).toHaveLength(2);
    expect(requests[1]?.headers.get('Idempotency-Key')).toBe(requests[0]?.headers.get('Idempotency-Key'));
    expect(await requests[1]?.json()).toEqual({ ...choice, expectedVersion: 0 });
  }
  expect(requests[0]?.headers.get('Authorization')).toBe(`Bearer ${started.runToken}`);
  expect(requests[0]?.headers.get('Idempotency-Key')).toBeTruthy();
  expect(await requests[0]?.json()).toEqual({ ...choice, expectedVersion: 0 });
  expect(result.current.failure).toBeNull();
  expect(runtime.queryClient.getQueryData(runQueryKey(runId))).toMatchObject({ version: 1 });
});
