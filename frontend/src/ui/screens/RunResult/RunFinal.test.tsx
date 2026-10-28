import { fireEvent, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderWithRuntime,
  type TestRuntime,
} from '../../../../test/renderWithRuntime';
import type { RunViewDto } from '../../../application/ports';
import { runQueryKey } from '../../../application/useRun';
import { RunFinal } from './RunFinal';
import { playUntilEnd, startRunOnDevice } from './testRuns';

const UNKNOWN_RUN_ID = '00000000-0000-4000-8000-000000000000';
const UNAVAILABLE = 'Esta partida no está disponible en este dispositivo.';

interface SeededRun {
  runtime: TestRuntime;
  run: RunViewDto;
}

/** Starts a run on this device (token in the store) and, unless `ending` is null, ends it. */
async function seedRun(ending: 'finished' | 'sacked' | null): Promise<SeededRun> {
  const runtime = createTestRuntime();
  const { gameApi, runTokenStore } = runtime;
  const started = await startRunOnDevice(gameApi, runTokenStore, mockFixtures.TEST_SEASON_ID);
  if (ending === null) return { runtime, run: started.run };
  const sackOptionId = ending === 'sacked' ? mockFixtures.SACK_OPTION_ID : null;
  return { runtime, run: await playUntilEnd(gameApi, started, sackOptionId) };
}

/** Records every GET of a run; returning nothing lets the original handler answer. */
function spyOnRunFetches(): string[] {
  const fetches: string[] = [];
  mockServer.use(
    http.get('*/api/runs/:runId', ({ request }) => {
      fetches.push(request.url);
    }),
  );
  return fetches;
}

function renderRunFinal(
  runtime: TestRuntime,
  runId: string,
  onPlayAgain = vi.fn(),
  onRunInPlay = vi.fn(),
) {
  const rendered = renderWithRuntime(
    <RunFinal runId={runId} onPlayAgain={onPlayAgain} onRunInPlay={onRunInPlay} />,
    { runtime },
  );
  return { ...rendered, onPlayAgain, onRunInPlay };
}

describe('RunFinal', () => {
  it('shows a loading status while the run loads', () => {
    const runtime = createTestRuntime();
    runtime.runTokenStore.save(UNKNOWN_RUN_ID, 'a-token');

    renderRunFinal(runtime, UNKNOWN_RUN_ID);

    expect(screen.getByRole('status')).toHaveTextContent('Cargando la partida…');
  });

  it('shows the result of a run that just ended from the cache, without fetching it again', async () => {
    const { runtime, run } = await seedRun('finished');
    runtime.queryClient.setQueryData(runQueryKey(run.runId), run);
    const fetches = spyOnRunFetches();

    renderRunFinal(runtime, run.runId);

    expect(screen.getByRole('heading', { level: 1, name: 'Final de la partida' })).toBeVisible();
    expect(screen.getByText('Temporada terminada')).toBeVisible();
    expect(fetches).toEqual([]);
  });

  it('loads the result after a reload with the token this device keeps', async () => {
    const { runtime, run } = await seedRun('finished');

    renderRunFinal(runtime, run.runId);

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Final de la partida' }),
    ).toBeVisible();
    expect(screen.getByText('Temporada terminada')).toBeVisible();
  });

  it('shows a sacked run as a dismissal', async () => {
    const { runtime, run } = await seedRun('sacked');

    renderRunFinal(runtime, run.runId);

    expect(await screen.findByText(/^Destituido en el bloque/)).toBeVisible();
    expect(screen.getByText(/^La directiva te destituyó/)).toBeVisible();
  });

  it('plays again through onPlayAgain', async () => {
    const { runtime, run } = await seedRun('finished');
    const { onPlayAgain } = renderRunFinal(runtime, run.runId);

    fireEvent.click(await screen.findByRole('button', { name: 'Jugar otra partida' }));

    expect(onPlayAgain).toHaveBeenCalledTimes(1);
  });

  it('says the run is not available on this device when there is no token for it', () => {
    renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(screen.getByText(UNAVAILABLE)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/');
  });

  it('moves the focus to the not-available notice title when it mounts', () => {
    renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(screen.getByRole('heading', { level: 1, name: 'Partida no disponible' })).toHaveFocus();
  });

  it('gives the link back home a touch-sized target', () => {
    renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveClass(
      'inline-flex',
      'min-h-touch',
      'items-center',
    );
  });

  it('goes home through onPlayAgain, without reloading, when the link back home is clicked', () => {
    const { onPlayAgain } = renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    const followed = fireEvent.click(screen.getByRole('link', { name: 'Volver al inicio' }));

    expect(followed).toBe(false);
    expect(onPlayAgain).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['with a modifier key', { ctrlKey: true }],
    ['with a button other than the main one', { button: 1 }],
  ])('leaves the link back home to the browser when it is clicked %s', (_case, init) => {
    const { onPlayAgain } = renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    const followed = fireEvent.click(screen.getByRole('link', { name: 'Volver al inicio' }), init);

    expect(followed).toBe(true);
    expect(onPlayAgain).not.toHaveBeenCalled();
  });

  it('forgets the token and says the run is not available when the API rejects it (403)', async () => {
    const { runtime, run } = await seedRun('finished');
    runtime.runTokenStore.save(run.runId, 'a-token-from-another-run');

    renderRunFinal(runtime, run.runId);

    expect(await screen.findByText(UNAVAILABLE)).toBeVisible();
    expect(runtime.runTokenStore.read(run.runId)).toBeNull();
  });

  it('lets the player retry when the run cannot be loaded', async () => {
    const { runtime, run } = await seedRun('finished');
    mockServer.use(
      http.get('*/api/runs/:runId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );
    renderRunFinal(runtime, run.runId);

    fireEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Final de la partida' }),
    ).toBeVisible();
  });

  it('hands a run still in play back to its page through onRunInPlay', async () => {
    const { runtime, run } = await seedRun(null);

    const { onRunInPlay } = renderRunFinal(runtime, run.runId);

    await waitFor(() => {
      expect(onRunInPlay).toHaveBeenCalledWith(run.runId);
    });
    expect(onRunInPlay).toHaveBeenCalledTimes(1);
    expect(screen.queryByText('Final de la partida')).not.toBeInTheDocument();
  });

  it('has no accessibility violations for an ended run', async () => {
    const { runtime, run } = await seedRun('sacked');
    const { container } = renderRunFinal(runtime, run.runId);
    await screen.findByRole('heading', { level: 1, name: 'Final de la partida' });

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations when the run is not available', async () => {
    const { container } = renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(await axe(container)).toHaveNoViolations();
  });
});
