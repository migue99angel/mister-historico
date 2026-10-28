import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Suspense } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  renderWithRuntime,
} from '../../../test/renderWithRuntime';

import { playUntilEnd, startRunOnDevice } from '../../ui/screens/RunResult/testRuns';
import { App } from '../App';
import { NativeRouter } from '../nativeRouter';
import type * as RunFinalRouteModule from './RunFinalRoute';
import type { RunFinalRouteProps } from './RunFinalRoute';

// Probe in place of the mounted screen: proves Routes.tsx passes the right props and
// callbacks. Keep it now that the screen has landed (T4.6a); only the screen tests below changed.
vi.mock('./RunFinalRoute', () => ({
  RunFinalRoute: ({ runId, onPlayAgain }: RunFinalRouteProps) => (
    <section>
      <p>Parámetro: {runId}</p>
      <button
        type="button"
        onClick={() => {
          onPlayAgain();
        }}
      >
        Jugar otra vez
      </button>
    </section>
  ),
}));

describe('RunFinalRoute mount point (/partida/:id/final)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/partida/run-1/final');
  });

  it('receives the route parameter as the runId prop', async () => {
    render(<App startMocks={() => Promise.resolve()} />);

    expect(await screen.findByText('Parámetro: run-1')).toBeInTheDocument();
  });

  it('goes home to play again through onPlayAgain', async () => {
    render(<App startMocks={() => Promise.resolve()} />);
    const historyLength = window.history.length;

    fireEvent.click(await screen.findByRole('button', { name: 'Jugar otra vez' }));

    expect(window.location.pathname).toBe('/');
    expect(window.history.length).toBe(historyLength + 1);
  });

  it('mounts the final screen, loaded lazily, with the ended run of this device', async () => {
    const { RunFinalRoute } = await vi.importActual<typeof RunFinalRouteModule>('./RunFinalRoute');
    const runtime = createTestRuntime();
    const { gameApi, runTokenStore } = runtime;
    const started = await startRunOnDevice(gameApi, runTokenStore, mockFixtures.TEST_SEASON_ID);
    const { runId } = started.run;
    // Sack the manager in the first block: confront the board, then simulate.
    await playUntilEnd(gameApi, started, mockFixtures.SACK_OPTION_ID);

    renderWithRuntime(
      <NativeRouter>
        <Suspense fallback={<p>Cargando…</p>}>
          <RunFinalRoute runId={runId} onPlayAgain={() => undefined} />
        </Suspense>
      </NativeRouter>,
      { runtime },
    );

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Final de la partida' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^La directiva te destituyó/)).toBeInTheDocument();
  });

  it('replaces the final page with the run page while the run is still in play', async () => {
    const { RunFinalRoute } = await vi.importActual<typeof RunFinalRouteModule>('./RunFinalRoute');
    const runtime = createTestRuntime();
    const { run } = await startRunOnDevice(
      runtime.gameApi,
      runtime.runTokenStore,
      mockFixtures.TEST_SEASON_ID,
    );
    const { runId } = run;
    window.history.replaceState(null, '', `/partida/${runId}/final`);
    const historyLength = window.history.length;

    renderWithRuntime(
      <NativeRouter>
        <Suspense fallback={<p>Cargando…</p>}>
          <RunFinalRoute runId={runId} onPlayAgain={() => undefined} />
        </Suspense>
      </NativeRouter>,
      { runtime },
    );

    await waitFor(() => {
      expect(window.location.pathname).toBe(`/partida/${runId}`);
    });
    expect(window.history.length).toBe(historyLength);
  });

  it('mounts the final screen, which says a run without a token is not available', async () => {
    const { RunFinalRoute } = await vi.importActual<typeof RunFinalRouteModule>('./RunFinalRoute');

    renderWithRuntime(
      <NativeRouter>
        <Suspense fallback={<p>Cargando…</p>}>
          <RunFinalRoute runId="run-1" onPlayAgain={() => undefined} />
        </Suspense>
      </NativeRouter>,
    );

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
  });
});
