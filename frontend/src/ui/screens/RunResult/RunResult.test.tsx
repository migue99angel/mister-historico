import { fireEvent, render, screen, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';

import type {
  BlockSummaryDto,
  MatchReportDto,
  StandingRowDto,
  TeamRefDto,
} from '../../../application/ports';
import { RunResult, type TerminalRunView } from './RunResult';

// Synthetic Test FC data only: nothing here is real.
function team(name: string, isUser = false): TeamRefDto {
  return {
    clubSeasonId: `${name.toLowerCase().replaceAll(' ', '-')}-2000-01`,
    name,
    shortName: name.slice(0, 3).toUpperCase(),
    colors: { primary: '#1f6f43', secondary: '#f4f1e8' },
    isUser,
  };
}

const TEST_FC = team('Test FC', true);
const RIVAL = team('Rival Test');
const ATLETICO = team('Atlético Prueba');

function match(overrides: Partial<MatchReportDto> = {}): MatchReportDto {
  return {
    fixtureId: 'liga-test-38',
    competitionId: 'liga-test',
    competitionName: 'Liga Test',
    round: 'Jornada 38',
    date: '2001-05-20',
    home: TEST_FC,
    away: RIVAL,
    homeGoals: 2,
    awayGoals: 1,
    extraTime: null,
    penalties: null,
    venue: 'home',
    isKeyMatch: false,
    keyMatchLabel: null,
    userResult: 'win',
    ...overrides,
  };
}

function row(position: number, ref: TeamRefDto, points: number): StandingRowDto {
  return {
    position,
    previousPosition: position,
    team: ref,
    played: 38,
    won: 0,
    drawn: 0,
    lost: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    points,
  };
}

function summary(overrides: Partial<BlockSummaryDto> = {}): BlockSummaryDto {
  return {
    blockNumber: 5,
    label: 'Abril-mayo',
    results: [
      match(),
      match({
        fixtureId: 'copa-test-final',
        competitionId: 'copa-test',
        competitionName: 'Copa Test',
        home: ATLETICO,
        away: TEST_FC,
        homeGoals: 1,
        awayGoals: 1,
        extraTime: { home: 0, away: 0 },
        penalties: { home: 3, away: 4 },
        venue: 'neutral',
        isKeyMatch: true,
        keyMatchLabel: 'Final de copa',
      }),
    ],
    standings: [
      {
        competitionId: 'liga-test',
        competitionName: 'Liga Test',
        rows: [row(1, RIVAL, 80), row(2, TEST_FC, 77), row(3, ATLETICO, 70)],
      },
    ],
    events: [],
    injuries: [],
    ...overrides,
  };
}

function run(overrides: Partial<TerminalRunView> = {}): TerminalRunView {
  return {
    runId: '00000000-0000-4000-8000-000000000001',
    seasonId: 'test-fc-2000-01',
    status: 'finished',
    version: 12,
    block: { number: 5, total: 5, label: 'Abril-mayo' },
    pendingDilemmas: [],
    decisions: [],
    state: { morale: 60, boardConfidence: 70, fitness: 80 },
    squad: { size: 0, averageRating: 0, players: [] },
    tactic: { style: 'balanced', system: '4-4-2' },
    competitionPriorities: [],
    lastBlockSummary: summary(),
    sackedMonth: null,
    ...overrides,
  };
}

const sackedRun = run({
  status: 'sacked',
  block: { number: 3, total: 5, label: 'Enero-febrero' },
  lastBlockSummary: summary({ blockNumber: 3, label: 'Enero-febrero' }),
  sackedMonth: 2,
});

function renderResult(view: TerminalRunView, onPlayAgain = vi.fn()) {
  return render(<RunResult run={view} onPlayAgain={onPlayAgain} />);
}

function segmentStates(container: HTMLElement): (string | undefined)[] {
  return [...container.querySelectorAll<HTMLElement>('[data-segment]')].map(
    (segment) => segment.dataset.segment,
  );
}

describe('RunResult', () => {
  it('shows a finished run as the end of the season', () => {
    const { container } = renderResult(run());

    expect(screen.getByRole('heading', { level: 1, name: 'Final de la partida' })).toBeVisible();
    expect(screen.getByText('Temporada terminada')).toBeVisible();
    expect(screen.getByText('Has llegado al final de la temporada.')).toBeVisible();
    expect(segmentStates(container)).toEqual(Array<string>(5).fill('played'));
  });

  it('shows the last block results of a finished run', () => {
    renderResult(run());

    const lastBlock = screen.getByRole('region', { name: 'Último bloque' });
    expect(within(lastBlock).getByText('Abril-mayo · 2 victorias')).toBeVisible();
    expect(within(lastBlock).getAllByRole('listitem')).toHaveLength(2);
    expect(within(lastBlock).getByText('2–1')).toBeVisible();
    expect(within(lastBlock).getByText('Final de copa')).toBeVisible();
    expect(within(lastBlock).getByText('tras la prórroga, 3-4 en los penaltis')).toBeVisible();
  });

  it('marks the user team in each result of the last block', () => {
    renderResult(run());

    const lastBlock = screen.getByRole('region', { name: 'Último bloque' });
    expect(within(lastBlock).getAllByText('(tu equipo)')).toHaveLength(2);
  });

  it('shows the final league table of a finished run with the user team highlighted', () => {
    renderResult(run());

    const standings = screen.getByRole('region', { name: 'Clasificación final' });
    const table = within(standings).getByRole('table', { name: 'Liga Test' });
    const userRow = within(table)
      .getAllByRole('row')
      .find((tableRow) => tableRow.getAttribute('aria-current') === 'true');
    expect(userRow).toHaveTextContent('Test FC');
    expect(userRow).toHaveTextContent('77');
  });

  it('prefers the league table over a group table that also lists the user team', () => {
    const groupTable = {
      competitionId: 'copa-test',
      competitionName: 'Copa Test',
      stageId: 'grupos',
      groupId: 'a',
      rows: [row(1, TEST_FC, 12), row(2, RIVAL, 9)],
    };
    const leagueTable = summary().standings[0];
    if (!leagueTable) throw new Error('The fixture needs a league table.');
    renderResult(run({ lastBlockSummary: summary({ standings: [groupTable, leagueTable] }) }));

    const standings = screen.getByRole('region', { name: 'Clasificación final' });
    expect(within(standings).getByRole('table', { name: 'Liga Test' })).toBeVisible();
    expect(within(standings).queryByRole('table', { name: 'Copa Test' })).not.toBeInTheDocument();
  });

  it('leaves out the standings when no table of the last block lists the user team', () => {
    renderResult(run({ lastBlockSummary: summary({ standings: [] }) }));

    expect(screen.getByRole('region', { name: 'Último bloque' })).toBeVisible();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('shows a sacked run as a dismissal, not as a finished season', () => {
    const { container } = renderResult(sackedRun);

    expect(screen.getByText('Destituido en el bloque 3 de 5')).toBeVisible();
    expect(screen.queryByText('Temporada terminada')).not.toBeInTheDocument();
    expect(segmentStates(container)).toEqual(['played', 'played', 'sacked', 'pending', 'pending']);
  });

  it('names the month of the dismissal when the run knows it', () => {
    renderResult(sackedRun);

    expect(screen.getByText('La directiva te destituyó en febrero.')).toBeVisible();
  });

  it('reports the dismissal without a month when the run does not know it', () => {
    renderResult({ ...sackedRun, sackedMonth: null });

    expect(screen.getByText('La directiva te destituyó.')).toBeVisible();
  });

  it('titles the standings of a sacked run as the table at the dismissal', () => {
    renderResult(sackedRun);

    expect(screen.getByRole('region', { name: 'Clasificación al ser destituido' })).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Clasificación final' })).not.toBeInTheDocument();
  });

  it('explains there is no last block summary when the run has none', () => {
    renderResult(run({ lastBlockSummary: null }));

    expect(screen.getByText('No hay resumen del último bloque.')).toBeVisible();
    expect(screen.queryByRole('region', { name: 'Último bloque' })).not.toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jugar otra partida' })).toBeVisible();
  });

  it('starts another run when the player taps «Jugar otra partida»', () => {
    const onPlayAgain = vi.fn();
    renderResult(run(), onPlayAgain);

    fireEvent.click(screen.getByRole('button', { name: 'Jugar otra partida' }));

    expect(onPlayAgain).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['finished', run()],
    ['sacked', sackedRun],
  ])('shows no score, percentile or historical verdict for a %s run', (_status, view) => {
    renderResult(view);

    expect(screen.queryByText(/puntuación/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/percentil/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/superaste|igualaste la historia|te quedaste por debajo/i),
    ).not.toBeInTheDocument();
  });

  it('has no accessibility violations for a finished run', async () => {
    const { container } = renderResult(run());

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations for a sacked run', async () => {
    const { container } = renderResult(sackedRun);

    expect(await axe(container)).toHaveNoViolations();
  });
});
