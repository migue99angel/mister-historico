import { render, screen, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { MiniStandings, type MiniStandingsRow } from './MiniStandings';

const rows: MiniStandingsRow[] = [
  {
    position: 1,
    teamName: 'Union Ficticia',
    played: 4,
    points: 10,
    change: { direction: 'same', symbol: '=', text: 'Mantiene el puesto' },
  },
  {
    position: 2,
    teamName: 'Test FC',
    played: 4,
    points: 7,
    isUser: true,
    change: { direction: 'up', symbol: '▲3', text: 'Sube 3 puestos' },
  },
  {
    position: 3,
    teamName: 'Rovers Prueba',
    played: 4,
    points: 6,
    change: { direction: 'down', symbol: '▼1', text: 'Baja 1 puesto' },
  },
  {
    position: 4,
    teamName: 'Athletic Ensayo',
    played: 4,
    points: 5,
    change: { direction: 'new', symbol: null, text: null },
  },
];

describe('MiniStandings', () => {
  it('is a table named by its competition', () => {
    render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    const table = screen.getByRole('table', { name: 'Liga Test' });
    expect(within(table).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'Pos.',
      'Equipo',
      'PJ',
      'Pts',
    ]);
  });

  it('lists one row per team in order', () => {
    render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    const [, ...bodyRows] = screen.getAllByRole('row');
    expect(bodyRows.map((row) => within(row).getByRole('rowheader').textContent)).toEqual([
      'Union Ficticia',
      'Test FC',
      'Rovers Prueba',
      'Athletic Ensayo',
    ]);
  });

  it("marks the player's team as the current row", () => {
    render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    expect(screen.getByRole('row', { current: true })).toHaveTextContent('Test FC');
  });

  it.each([
    ['▲3', 'Sube 3 puestos'],
    ['▼1', 'Baja 1 puesto'],
    ['=', 'Mantiene el puesto'],
  ])('shows the position change %s and announces «%s»', (symbol, text) => {
    render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    expect(screen.getByText(symbol)).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText(text)).toHaveClass('sr-only');
  });

  it('shows no change for a team without a previous position', () => {
    render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    const newcomer = screen.getByRole('row', { name: /Athletic Ensayo/ });
    const [positionCell] = within(newcomer).getAllByRole('cell');
    expect(positionCell?.textContent).toBe('4');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<MiniStandings competitionName="Liga Test" rows={rows} />);

    expect(await axe(container)).toHaveNoViolations();
  });
});
