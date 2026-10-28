import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { mockFixtures, renderWithRuntime } from '../../../test/renderWithRuntime';
import { App } from '../App';
import { NativeRouter } from '../nativeRouter';
import type * as HomeRouteModule from './HomeRoute';
import type { HomeRouteProps } from './HomeRoute';

// Probe in place of the mounted screen: proves Routes.tsx passes the right props and
// callbacks. Keep it when the screen lands (T4.4); adapt only the screen test below.
vi.mock('./HomeRoute', () => ({
  HomeRoute: ({ onSeasonChosen }: HomeRouteProps) => (
    <button
      type="button"
      onClick={() => {
        onSeasonChosen('test-fc-2000-01');
      }}
    >
      Elegir temporada
    </button>
  ),
}));

describe('HomeRoute mount point (/)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('opens the team page of the chosen season through onSeasonChosen', async () => {
    render(<App startMocks={() => Promise.resolve()} />);
    const historyLength = window.history.length;

    fireEvent.click(await screen.findByRole('button', { name: 'Elegir temporada' }));

    expect(window.location.pathname).toBe('/equipo/test-fc-2000-01');
    expect(window.history.length).toBe(historyLength + 1);
  });

  it('shows the title and tagline the home e2e test expects', async () => {
    const { HomeRoute } = await vi.importActual<typeof HomeRouteModule>('./HomeRoute');

    renderWithRuntime(
      <NativeRouter>
        <HomeRoute onSeasonChosen={() => undefined} />
      </NativeRouter>,
    );

    expect(screen.getByRole('heading', { level: 1, name: 'Míster Histórico' })).toBeInTheDocument();
    expect(screen.getByText('¿Lo habrías hecho mejor que el míster?')).toBeInTheDocument();
  });

  it('mounts the season picker, which reports the chosen season', async () => {
    const { HomeRoute } = await vi.importActual<typeof HomeRouteModule>('./HomeRoute');
    const onSeasonChosen = vi.fn<(seasonId: string) => void>();

    renderWithRuntime(
      <NativeRouter>
        <HomeRoute onSeasonChosen={onSeasonChosen} />
      </NativeRouter>,
    );
    fireEvent.click(await screen.findByRole('button', { name: 'Elegir Test FC 2000-01' }));

    expect(onSeasonChosen).toHaveBeenCalledExactlyOnceWith(mockFixtures.TEST_SEASON_ID);
  });
});
