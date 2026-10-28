import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { mockFixtures, renderWithRuntime } from '../../../test/renderWithRuntime';
import { App } from '../App';
import { NativeRouter } from '../nativeRouter';
import type * as SeasonRouteModule from './SeasonRoute';
import type { SeasonRouteProps } from './SeasonRoute';

// Probe in place of the mounted screen: proves Routes.tsx passes the right props and
// callbacks. Keep it when the screen lands (T4.4); adapt only the screen test below.
vi.mock('./SeasonRoute', () => ({
  SeasonRoute: ({ seasonId, onRunStarted }: SeasonRouteProps) => (
    <section>
      <p>Parámetro: {seasonId}</p>
      <button
        type="button"
        onClick={() => {
          onRunStarted('run-1');
        }}
      >
        Empezar la partida
      </button>
    </section>
  ),
}));

describe('SeasonRoute mount point (/equipo/:id)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/equipo/test-fc-2000-01');
  });

  it('receives the route parameter as the seasonId prop', async () => {
    render(<App startMocks={() => Promise.resolve()} />);

    expect(await screen.findByText('Parámetro: test-fc-2000-01')).toBeInTheDocument();
  });

  it('opens the run page once the run has started through onRunStarted', async () => {
    render(<App startMocks={() => Promise.resolve()} />);
    const historyLength = window.history.length;

    fireEvent.click(await screen.findByRole('button', { name: 'Empezar la partida' }));

    expect(window.location.pathname).toBe('/partida/run-1');
    expect(window.history.length).toBe(historyLength + 1);
  });

  it('mounts the season intro with the context of the season', async () => {
    const { SeasonRoute } = await vi.importActual<typeof SeasonRouteModule>('./SeasonRoute');

    renderWithRuntime(
      <NativeRouter>
        <SeasonRoute seasonId={mockFixtures.TEST_SEASON_ID} onRunStarted={() => undefined} />
      </NativeRouter>,
    );

    expect(await screen.findByRole('heading', { level: 1, name: 'Test FC' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Objetivos de la directiva' })).toBeInTheDocument();
  });

  it('reports the started run through onRunStarted', async () => {
    const { SeasonRoute } = await vi.importActual<typeof SeasonRouteModule>('./SeasonRoute');
    const onRunStarted = vi.fn<(runId: string) => void>();

    const { runTokenStore } = renderWithRuntime(
      <NativeRouter>
        <SeasonRoute seasonId={mockFixtures.TEST_SEASON_ID} onRunStarted={onRunStarted} />
      </NativeRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Empezar' }));

    await waitFor(() => {
      expect(onRunStarted).toHaveBeenCalledOnce();
    });
    const [runId] = onRunStarted.mock.calls[0] ?? [''];
    expect(runTokenStore.read(runId)).not.toBeNull();
  });

  it('goes back home from an unknown season', async () => {
    const { SeasonRoute } = await vi.importActual<typeof SeasonRouteModule>('./SeasonRoute');

    renderWithRuntime(
      <NativeRouter>
        <SeasonRoute seasonId="no-such-season" onRunStarted={() => undefined} />
      </NativeRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Volver al inicio' }));

    expect(window.location.pathname).toBe('/');
  });
});
