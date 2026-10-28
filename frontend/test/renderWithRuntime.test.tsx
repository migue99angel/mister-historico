import { useQuery } from '@tanstack/react-query';
import { screen } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { describe, expect, it } from 'vitest';

import { useGameApi } from '../src/application/gameApi';
import { useRunTokenStore } from '../src/application/runTokenStore';
import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderHookWithRuntime,
  renderWithRuntime,
} from './renderWithRuntime';

function SeasonIds() {
  const gameApi = useGameApi();
  const seasons = useQuery({ queryKey: ['seasons'], queryFn: () => gameApi.listSeasons() });

  if (seasons.isError) return <p role="alert">Error</p>;
  if (!seasons.data) return <p role="status">Cargando</p>;
  return (
    <ul>
      {seasons.data.items.map((season) => (
        <li key={season.id}>{season.id}</li>
      ))}
    </ul>
  );
}

describe('renderWithRuntime', () => {
  it('serves application hooks with the real HTTP adapter against the MSW handlers', async () => {
    renderWithRuntime(<SeasonIds />);

    expect(await screen.findByText(mockFixtures.TEST_SEASON_ID)).toBeInTheDocument();
  });

  it('surfaces a failed query at once because the query client never retries', async () => {
    mockServer.use(http.get('*/api/seasons', () => HttpResponse.text('down', { status: 500 })));

    renderWithRuntime(<SeasonIds />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Error');
  });

  it('starts every runtime from a fresh mock backend', async () => {
    const first = createTestRuntime();
    const started = await first.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });

    const second = createTestRuntime();

    await expect(second.gameApi.getRun(started.run.runId, started.runToken)).rejects.toMatchObject({
      status: 404,
    });
  });
});

describe('renderHookWithRuntime', () => {
  it('shares its in-memory RunTokenStore with the hook under test', () => {
    const { result, runTokenStore } = renderHookWithRuntime(() => useRunTokenStore());

    result.current.save('run-1', 'token-1');

    expect(runTokenStore.read('run-1')).toBe('token-1');
  });

  it('reuses a runtime prepared before rendering, keeping its seeded runs', async () => {
    const runtime = createTestRuntime();
    const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
    runtime.runTokenStore.save(started.run.runId, started.runToken);

    const { result } = renderHookWithRuntime(() => useRunTokenStore(), { runtime });

    expect(result.current.read(started.run.runId)).toBe(started.runToken);
  });
});
