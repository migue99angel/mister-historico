import { act, screen, within } from '@testing-library/react';
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

    const season = await screen.findByRole('region', { name: 'Test FC 2000-01' });
    expect(season).toHaveTextContent('Míster real: Ramon Prueba');
    expect(screen.getByRole('region', { name: 'Rovers Prueba 2001-02' })).toBeInTheDocument();
  });

  it('names each season by club and season, so two seasons of a club differ', async () => {
    const summary = {
      id: 'test-fc-2001-02',
      clubName: 'Test FC',
      shortName: 'TFC',
      seasonLabel: '2001-02',
      historicalManager: 'Ramon Prueba',
      colors: { primary: '#1d4ed8', secondary: '#f8fafc' },
    };
    mockServer.use(
      http.get('*/api/seasons', () =>
        HttpResponse.json({
          items: [{ ...summary, id: mockFixtures.TEST_SEASON_ID, seasonLabel: '2000-01' }, summary],
        }),
      ),
    );
    renderPicker();

    expect(await screen.findByRole('region', { name: 'Test FC 2000-01' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Test FC 2001-02' })).toBeInTheDocument();
  });

  it('reports the season the player chooses', async () => {
    const onSeasonChosen = vi.fn<(seasonId: string) => void>();
    renderPicker(onSeasonChosen);

    const season = await screen.findByRole('region', { name: 'Test FC 2000-01' });
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

    expect(await screen.findByRole('region', { name: 'Test FC 2000-01' })).toBeInTheDocument();
  });

  it('keeps the seasons on screen when a later refetch fails', async () => {
    const { queryClient } = renderPicker();
    await screen.findByRole('region', { name: 'Test FC 2000-01' });
    mockServer.use(
      http.get('*/api/seasons', () => HttpResponse.text('down', { status: 500 }), { once: true }),
    );

    await act(() => queryClient.refetchQueries());

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hemos podido actualizar las temporadas.',
    );
    expect(screen.getByRole('region', { name: 'Test FC 2000-01' })).toBeInTheDocument();
  });

  it('says so when there are no seasons to play yet', async () => {
    mockServer.use(http.get('*/api/seasons', () => HttpResponse.json({ items: [] })));
    renderPicker();

    expect(await screen.findByText('Todavía no hay temporadas disponibles.')).toBeInTheDocument();
  });

  it('has no accessibility violations once the seasons are listed', async () => {
    const { container } = renderPicker();
    await screen.findByRole('region', { name: 'Test FC 2000-01' });

    expect(await axe(container)).toHaveNoViolations();
  });
});
