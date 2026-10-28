import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from '../App';
import { NativeRouter } from '../nativeRouter';
import type * as RunFinalRouteModule from './RunFinalRoute';
import type { RunFinalRouteProps } from './RunFinalRoute';

// Probe in place of the mounted screen: proves Routes.tsx passes the right props and
// callbacks. Keep it when the screen lands (T4.6a); adapt only the screen test below.
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

  it('currently mounts the placeholder page with its identifier', async () => {
    const { RunFinalRoute } = await vi.importActual<typeof RunFinalRouteModule>('./RunFinalRoute');

    render(
      <NativeRouter>
        <RunFinalRoute runId="run-1" onPlayAgain={() => undefined} />
      </NativeRouter>,
    );

    expect(
      screen.getByRole('heading', { level: 1, name: 'Resultado de la partida' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Identificador: run-1')).toBeInTheDocument();
  });
});
