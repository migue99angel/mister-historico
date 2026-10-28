import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
import { SeasonIntro, type SeasonIntroProps } from './SeasonIntro';

const problem = (status: number, code: string) =>
  HttpResponse.json(
    { type: 'about:blank', title: 'Failure', status, code },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

function renderIntro(props: Partial<SeasonIntroProps> = {}, runtime?: TestRuntime) {
  return renderWithRuntime(
    <SeasonIntro
      seasonId={mockFixtures.TEST_SEASON_ID}
      onRunStarted={() => undefined}
      onBackHome={() => undefined}
      {...props}
    />,
    runtime ? { runtime } : {},
  );
}

const startButton = () => screen.findByRole('button', { name: 'Empezar' });

describe('SeasonIntro', () => {
  it('tells the player the season is loading', () => {
    renderIntro();

    expect(screen.getByRole('status')).toHaveTextContent('Cargando la temporada…');
  });

  it('presents the club, the season and its historical manager', async () => {
    renderIntro();

    expect(await screen.findByRole('heading', { level: 1, name: 'Test FC' })).toBeInTheDocument();
    expect(screen.getByText('Temporada 2000-01 · Míster real: Ramon Prueba')).toBeInTheDocument();
    expect(
      screen.getByText('The board hires you after a mid-table finish. The fans want a title.'),
    ).toBeInTheDocument();
  });

  it('lists the board objectives', async () => {
    renderIntro();

    const objectives = await screen.findByRole('region', { name: 'Objetivos de la directiva' });
    expect(
      within(objectives)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['Finish the league in the top four.', 'Reach the semi-finals of the cup.']);
  });

  it('summarises the squad with its key players', async () => {
    renderIntro();

    const squad = await screen.findByRole('region', { name: 'Plantilla' });
    expect(squad).toHaveTextContent('22 jugadores · media 74,5');
    expect(within(squad).getByText('Ivan Delantero')).toBeInTheDocument();
    expect(within(squad).getByText('Delantero · 84')).toBeInTheDocument();
  });

  it('lists the competitions and the number of blocks', async () => {
    renderIntro();

    const season = await screen.findByRole('region', { name: 'La temporada' });
    expect(season).toHaveTextContent('Liga Test');
    expect(season).toHaveTextContent('Copa Test');
    expect(season).toHaveTextContent('Se juega en 5 bloques.');
  });

  it('starts the run, keeps its token and reports the run id', async () => {
    const onRunStarted = vi.fn<(runId: string) => void>();
    const { runTokenStore } = renderIntro({ onRunStarted });

    await userEvent.click(await startButton());

    await vi.waitFor(() => {
      expect(onRunStarted).toHaveBeenCalledOnce();
    });
    const [runId] = onRunStarted.mock.calls[0] ?? [''];
    expect(runTokenStore.read(runId)).not.toBeNull();
  });

  it('starts a single run on a double tap', async () => {
    const runtime = createTestRuntime();
    const startRun = vi.spyOn(runtime.gameApi, 'startRun');
    const onRunStarted = vi.fn<(runId: string) => void>();
    renderIntro({ onRunStarted }, runtime);

    await userEvent.dblClick(await startButton());

    await vi.waitFor(() => {
      expect(onRunStarted).toHaveBeenCalled();
    });
    expect(startRun).toHaveBeenCalledOnce();
    expect(onRunStarted).toHaveBeenCalledOnce();
  });

  it('shows why the run could not start and lets the player retry', async () => {
    mockServer.use(http.post('*/api/runs', () => problem(503, 'unavailable'), { once: true }));
    const onRunStarted = vi.fn<(runId: string) => void>();
    renderIntro({ onRunStarted });

    await userEvent.click(await startButton());

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hemos podido empezar la partida.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    await vi.waitFor(() => {
      expect(onRunStarted).toHaveBeenCalledOnce();
    });
  });

  it('says the season does not exist and offers the way back home', async () => {
    const onBackHome = vi.fn<() => void>();
    renderIntro({ seasonId: 'no-such-season', onBackHome });

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Temporada no encontrada' }),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Volver al inicio' }));

    expect(onBackHome).toHaveBeenCalledOnce();
  });

  it('shows an error with a retry when the season cannot load', async () => {
    mockServer.use(
      http.get('*/api/seasons/:seasonId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );
    renderIntro();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hemos podido cargar la temporada.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Test FC' })).toBeInTheDocument();
  });

  it('keeps the season on screen when a later refetch fails', async () => {
    const { queryClient } = renderIntro();
    await screen.findByRole('heading', { level: 1, name: 'Test FC' });
    mockServer.use(
      http.get('*/api/seasons/:seasonId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );

    await act(() => queryClient.refetchQueries());

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No hemos podido actualizar la temporada.',
    );
    expect(screen.getByRole('heading', { level: 1, name: 'Test FC' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Empezar' })).toBeInTheDocument();
  });

  it('lets the player go back to choose another season', async () => {
    const onBackHome = vi.fn<() => void>();
    renderIntro({ onBackHome });

    await userEvent.click(await screen.findByRole('button', { name: 'Elegir otra temporada' }));

    expect(onBackHome).toHaveBeenCalledOnce();
  });

  it('does not let the player leave while the run is starting', async () => {
    let answer: () => void = () => undefined;
    const answered = new Promise<void>((resolve) => {
      answer = resolve;
    });
    mockServer.use(
      http.post('*/api/runs', async () => {
        await answered;
        return problem(503, 'unavailable');
      }),
    );
    const onBackHome = vi.fn<() => void>();
    renderIntro({ onBackHome });

    await userEvent.click(await startButton());
    const back = screen.getByRole('button', { name: 'Elegir otra temporada' });
    await userEvent.click(back);

    expect(back).toBeDisabled();
    expect(onBackHome).not.toHaveBeenCalled();
    answer();
    await screen.findByRole('alert');
  });

  it('has no accessibility violations once the season is shown', async () => {
    const { container } = renderIntro();
    await startButton();

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations for an unknown season', async () => {
    const { container } = renderIntro({ seasonId: 'no-such-season' });
    await screen.findByRole('heading', { level: 1, name: 'Temporada no encontrada' });

    expect(await axe(container)).toHaveNoViolations();
  });
});
