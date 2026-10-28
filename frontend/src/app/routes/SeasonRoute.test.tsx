import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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

  it('currently mounts the placeholder page with its identifier', async () => {
    const { SeasonRoute } = await vi.importActual<typeof SeasonRouteModule>('./SeasonRoute');

    render(
      <NativeRouter>
        <SeasonRoute seasonId="test-fc-2000-01" onRunStarted={() => undefined} />
      </NativeRouter>,
    );

    expect(
      screen.getByRole('heading', { level: 1, name: 'Contexto del equipo' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Identificador: test-fc-2000-01')).toBeInTheDocument();
  });
});
