import { render, screen, within } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';

import { mockFixtures } from '../../../../test/renderWithRuntime';
import type { BlockSummaryDto } from '../../../application/ports';
import { describeBlock } from '../../../domain/blockNarrative';
import { BlockSummary } from './BlockSummary';

function mixedSummary(): BlockSummaryDto {
  const matches = [...mockFixtures.resultsForBlock(2), ...mockFixtures.resultsForBlock(3)];
  function matchAt(index: number) {
    const match = matches[index];
    if (!match) throw new Error('Missing synthetic match');
    return match;
  }
  return {
    blockNumber: 1,
    label: 'Bloque Test',
    results: [
      { ...matchAt(5), fixtureId: 'last', date: '2001-02-02' },
      { ...matchAt(1), fixtureId: 'b', date: '2001-02-01' },
      { ...matchAt(2), fixtureId: 'a', date: '2001-02-01' },
      { ...matchAt(0), fixtureId: 'first', date: '2001-01-31', userResult: 'loss' },
    ],
    standings: [],
    events: [{ kind: 'board', date: '2001-02-02', text: 'Cierre de la directiva' }],
    injuries: [{ playerId: 'test', playerName: 'Jugador Test', date: '2001-02-02', daysOut: 5 }],
  };
}

describe('BlockSummary', () => {
  it('groups equal dates, sorts by date then fixture ID and preserves cup tie-breakers and text outcomes', () => {
    const summary = mixedSummary();
    const originalOrder = summary.results.map((match) => match.fixtureId);
    const { container, rerender } = render(
      <BlockSummary
        summary={summary}
        narrative={describeBlock(summary)}
        revealing
        visibleDates={2}
      />,
    );
    expect(
      screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent),
    ).toEqual(['31 ene 2001', '1 feb 2001']);
    const sharedDate = screen.getByRole('heading', { name: '1 feb 2001' }).closest('li');
    if (!sharedDate) throw new Error('Missing date group');
    const reports = within(sharedDate).getAllByRole('listitem');
    expect(reports).toHaveLength(2);
    expect(reports[0]).toHaveTextContent('Copa Test');
    expect(reports[0]).toHaveTextContent('2–1');
    expect(reports[0]).toHaveTextContent('tras la prórroga');
    expect(reports[0]).toHaveTextContent('Knockout tie');
    expect(reports[0]).toHaveTextContent('Victoria');
    expect(reports[1]).toHaveTextContent('Liga Test');
    expect(reports[1]).toHaveTextContent('Empate');
    expect(screen.getByText('Derrota')).toBeInTheDocument();
    expect(screen.queryByText(/penaltis/)).not.toBeInTheDocument();
    expect(screen.queryByText('Cierre de la directiva')).not.toBeInTheDocument();
    expect(screen.queryByText(/Parte médico/)).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('3 de 4 resultados');
    expect(container.querySelectorAll('time')).toHaveLength(2);
    rerender(<BlockSummary summary={summary} narrative={describeBlock(summary)} />);
    expect(screen.getByText('tras la prórroga, 3-4 en los penaltis')).toBeInTheDocument();
    expect(screen.getByText('Cierre de la directiva')).toBeInTheDocument();
    expect(screen.getByText(/Parte médico: Jugador Test/)).toBeInTheDocument();
    expect(summary.results.map((match) => match.fixtureId)).toEqual(originalOrder);
  });

  it('keeps the partial reveal accessible without exposing the closing narrative', async () => {
    const summary = mixedSummary();
    const { container } = render(
      <main>
        <h1>Partida</h1>
        <BlockSummary
          summary={summary}
          narrative={describeBlock(summary)}
          revealing
          visibleDates={2}
        />
      </main>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });

  it('names a key match even when the response supplies no special label', () => {
    const summary = mixedSummary();
    summary.results = summary.results.map((match) => ({
      ...match,
      isKeyMatch: true,
      keyMatchLabel: null,
    }));
    render(<BlockSummary summary={summary} narrative={describeBlock(summary)} />);
    expect(screen.getAllByText('Partido clave')).toHaveLength(summary.results.length);
  });

  it('keeps ISO dates in markup while presenting Spanish dates in a loaded summary', () => {
    const summary = mixedSummary();
    const { container } = render(
      <BlockSummary summary={summary} narrative={describeBlock(summary)} />,
    );
    expect(
      [...container.querySelectorAll('time')].map((time) => [time.dateTime, time.textContent]),
    ).toEqual([
      ['2001-01-31', '31 ene 2001'],
      ['2001-02-01', '1 feb 2001'],
      ['2001-02-02', '2 feb 2001'],
    ]);
  });

  it('keeps the live region empty outside a reveal', () => {
    const summary = mixedSummary();
    render(<BlockSummary summary={summary} narrative={describeBlock(summary)} />);
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  it('keeps both reveal controls before the results as the list grows', () => {
    const summary = mixedSummary();
    const onDecisions = vi.fn();
    const { rerender } = render(
      <BlockSummary
        summary={summary}
        narrative={describeBlock(summary)}
        revealing
        visibleDates={1}
        onDecisions={onDecisions}
      />,
    );
    const shortcut = screen.getByRole('button', { name: 'Ir a decisiones' });
    rerender(
      <BlockSummary
        summary={summary}
        narrative={describeBlock(summary)}
        revealing
        visibleDates={2}
        onDecisions={onDecisions}
      />,
    );
    const firstDate = screen.getAllByRole('heading', { level: 3 })[0];
    if (!firstDate) throw new Error('Missing date heading');
    expect(
      shortcut.compareDocumentPosition(firstDate) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Mostrar todos' }).compareDocumentPosition(shortcut) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('shows a complete, empty block without a skip control', () => {
    const summary = { ...mixedSummary(), results: [] };
    render(<BlockSummary summary={summary} narrative={describeBlock(summary)} />);
    expect(screen.getByText(/Sin partidos en este bloque/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mostrar todos' })).not.toBeInTheDocument();
  });
});
