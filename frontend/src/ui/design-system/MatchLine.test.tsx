import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { MatchLine } from './MatchLine';
import type { MatchLineResult } from './viewModels';

const win: MatchLineResult = {
  homeName: 'Test FC',
  awayName: 'Rovers Prueba',
  homeScore: 2,
  awayScore: 1,
  detailText: null,
  outcome: 'win',
  outcomeLabel: 'Victoria',
};

describe('MatchLine', () => {
  it('shows both teams and the score', () => {
    render(<MatchLine match={win} />);

    expect(screen.getByText('Test FC')).toBeInTheDocument();
    expect(screen.getByText('Rovers Prueba')).toBeInTheDocument();
    expect(screen.getByText('2–1')).toBeInTheDocument();
  });

  it.each([
    ['win', 'Victoria', 'V'],
    ['draw', 'Empate', 'E'],
    ['loss', 'Derrota', 'D'],
  ] as const)('announces a %s as «%s» behind a «%s» badge', (outcome, outcomeLabel, badge) => {
    render(<MatchLine match={{ ...win, outcome, outcomeLabel }} />);

    expect(screen.getByText(outcomeLabel)).toHaveClass('sr-only');
    expect(screen.getByText(badge)).toHaveAttribute('aria-hidden', 'true');
  });

  it.each(['tras la prórroga', '4-3 en los penaltis'])('shows how it was decided: %s', (detail) => {
    render(<MatchLine match={{ ...win, homeScore: 1, awayScore: 1, detailText: detail }} />);

    expect(screen.getByText(detail)).toBeInTheDocument();
  });

  it('shows the competition and highlights a key match', () => {
    render(<MatchLine match={win} competitionName="Copa Test" keyMatchLabel="Final" />);

    expect(screen.getByText('Copa Test')).toBeInTheDocument();
    expect(screen.getByText('Final')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <MatchLine
        match={{ ...win, detailText: 'tras la prórroga' }}
        competitionName="Liga Test"
        keyMatchLabel="Partido clave"
        userSide="home"
      />,
    );

    expect(await axe(container)).toHaveNoViolations();
  });
});
