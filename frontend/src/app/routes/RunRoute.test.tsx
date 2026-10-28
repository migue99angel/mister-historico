import { fireEvent, render, screen } from '@testing-library/react';
import { http } from 'msw';
import { Suspense, useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderWithRuntime,
} from '../../../test/renderWithRuntime';

import { App } from '../App';
import { NativeRouter } from '../nativeRouter';
import type * as RunRouteModule from './RunRoute';
import type { RunRouteProps } from './RunRoute';
import type * as SeasonRouteModule from './SeasonRoute';

// Probe in place of the mounted screen: proves Routes.tsx passes the right props and
// callbacks. Keep it when the screen lands (T4.5); adapt only the screen test below.
vi.mock('./RunRoute', () => ({
  RunRoute: ({ runId, onRunEnded }: RunRouteProps) => (
    <section>
      <p>Parámetro: {runId}</p>
      <button
        type="button"
        onClick={() => {
          onRunEnded('run-1');
        }}
      >
        Terminar la partida
      </button>
    </section>
  ),
}));

describe('RunRoute mount point (/partida/:id)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/partida/run-1');
  });

  it('receives the route parameter as the runId prop', async () => {
    render(<App startMocks={() => Promise.resolve()} />);

    expect(await screen.findByText('Parámetro: run-1')).toBeInTheDocument();
  });

  it('replaces the run page with its final page once the run ends through onRunEnded', async () => {
    render(<App startMocks={() => Promise.resolve()} />);
    const historyLength = window.history.length;

    fireEvent.click(await screen.findByRole('button', { name: 'Terminar la partida' }));

    expect(window.location.pathname).toBe('/partida/run-1/final');
    expect(window.history.length).toBe(historyLength);
  });

  it('mounts the run loop screen, loaded lazily, with the run of this device', async () => {
    const { RunRoute } = await vi.importActual<typeof RunRouteModule>('./RunRoute');
    const runtime = createTestRuntime();
    const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
    runtime.runTokenStore.save(started.run.runId, started.runToken);

    renderWithRuntime(
      <NativeRouter>
        <Suspense fallback={<p>Cargando…</p>}>
          <RunRoute runId={started.run.runId} onRunEnded={() => undefined} />
        </Suspense>
      </NativeRouter>,
      { runtime },
    );

    expect(
      await screen.findByRole('heading', { name: 'Decisiones del bloque' }),
    ).toBeInTheDocument();
  });

  it('mounts the run loop screen, which says a run without a token is not available', async () => {
    const { RunRoute } = await vi.importActual<typeof RunRouteModule>('./RunRoute');

    renderWithRuntime(
      <NativeRouter>
        <Suspense fallback={<p>Cargando…</p>}>
          <RunRoute runId="run-1" onRunEnded={() => undefined} />
        </Suspense>
      </NativeRouter>,
    );

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
  });

  it('opens the run started from the season page without fetching it again', async () => {
    const { RunRoute } = await vi.importActual<typeof RunRouteModule>('./RunRoute');
    const { SeasonRoute } = await vi.importActual<typeof SeasonRouteModule>('./SeasonRoute');
    const runFetches: string[] = [];
    mockServer.use(
      http.get('*/api/runs/:runId', ({ request }) => {
        runFetches.push(request.url);
      }),
    );
    // Season page, then run page, sharing one runtime as the app does between both routes.
    function SeasonThenRun() {
      const [runId, setRunId] = useState<string | null>(null);
      return (
        <Suspense fallback={<p>Cargando…</p>}>
          {runId === null ? (
            <SeasonRoute seasonId={mockFixtures.TEST_SEASON_ID} onRunStarted={setRunId} />
          ) : (
            <RunRoute runId={runId} onRunEnded={() => undefined} />
          )}
        </Suspense>
      );
    }

    renderWithRuntime(
      <NativeRouter>
        <SeasonThenRun />
      </NativeRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Empezar' }));

    expect(await screen.findByRole('heading', { name: 'Board meeting' })).toBeInTheDocument();
    expect(runFetches).toEqual([]);
  });
});
