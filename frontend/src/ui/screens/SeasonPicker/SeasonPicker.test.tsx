import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { mockFixtures, mockServer, renderWithRuntime } from '../../../../test/renderWithRuntime';
import { SeasonPicker } from './SeasonPicker';

function renderPicker(onSeasonChosen: (seasonId: string) => void = () => undefined) {
  return renderWithRuntime(<SeasonPicker onSeasonChosen={onSeasonChosen} />);
}

describe('SeasonPicker', () => {
  it('shows the game title and its tagline', () => {
    renderPicker();

    expect(screen.getByRole('heading', { level: 1, name: 'Míster Histórico' })).toBeInTheDocument();
    expect(screen.getByText('¿Lo habrías hecho mejor que el míster?')).toBeInTheDocument();
  });

  it('tells the player the seasons are loading', () => {
    renderPicker();

    expect(screen.getByRole('status')).toHaveTextContent('Cargando temporadas…');
  });

  it('lists each season with its club, season and historical manager', async () => {
    renderPicker();

    const season = await screen.findByRole('region', { name: 'Test FC' });
    expect(season).toHaveTextContent('2000-01');
    expect(season).toHaveTextContent('Míster real: Ramon Prueba');
    expect(screen.getByRole('region', { name: 'Rovers Prueba' })).toHaveTextContent('2001-02');
  });

  it('reports the season the player chooses', async () => {
    const onSeasonChosen = vi.fn<(seasonId: string) => void>();
    renderPicker(onSeasonChosen);

    const season = await screen.findByRole('region', { name: 'Test FC' });
    await userEvent.click(within(season).getByRole('button', { name: 'Elegir Test FC 2000-01' }));

    expect(onSeasonChosen).toHaveBeenCalledExactlyOnceWith(mockFixtures.TEST_SEASON_ID);
  });

  it('shows an error with a retry when the seasons cannot load', async () => {
    mockServer.use(
      http.get('*/api/seasons', () => HttpResponse.text('down', { status: 500 }), { once: true }),
    );
    renderPicker();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hemos podido cargar las temporadas.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('region', { name: 'Test FC' })).toBeInTheDocument();
  });

  it('says so when there are no seasons to play yet', async () => {
    mockServer.use(http.get('*/api/seasons', () => HttpResponse.json({ items: [] })));
    renderPicker();

    expect(await screen.findByText('Todavía no hay temporadas disponibles.')).toBeInTheDocument();
  });

  it('has no accessibility violations once the seasons are listed', async () => {
    const { container } = renderPicker();
    await screen.findByRole('region', { name: 'Test FC' });

    expect(await axe(container)).toHaveNoViolations();
  });
});
