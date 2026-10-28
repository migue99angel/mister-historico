import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it } from 'vitest';

import { BlockProgress } from './BlockProgress';
import type { RunStatus, SeasonProgress } from './viewModels';

const inProgress: SeasonProgress = {
  blockNumber: 3,
  totalBlocks: 5,
  playedBlocks: 2,
  percent: 40,
  isOver: false,
  title: 'Bloque 3 de 5',
  subtitle: 'Diciembre-enero',
};
const finished: SeasonProgress = {
  ...inProgress,
  blockNumber: 5,
  playedBlocks: 5,
  percent: 100,
  isOver: true,
  title: 'Temporada terminada',
  subtitle: 'Abril-mayo',
};
const sacked: SeasonProgress = {
  ...inProgress,
  playedBlocks: 3,
  percent: 60,
  isOver: true,
  title: 'Destituido en el bloque 3 de 5',
};

function segmentStates(container: HTMLElement): (string | undefined)[] {
  return [...container.querySelectorAll<HTMLElement>('[data-segment]')].map(
    (segment) => segment.dataset.segment,
  );
}

describe('BlockProgress', () => {
  it('shows the progress title and the block label', () => {
    render(<BlockProgress progress={inProgress} />);

    expect(screen.getByText('Bloque 3 de 5')).toBeInTheDocument();
    expect(screen.getByText('Diciembre-enero')).toBeInTheDocument();
  });

  it('exposes the played blocks as a progress bar', () => {
    render(<BlockProgress progress={inProgress} />);

    const bar = screen.getByRole('progressbar', { name: 'Progreso de la temporada' });
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '5');
    expect(bar).toHaveAttribute('aria-valuenow', '2');
    expect(bar).toHaveAttribute('aria-valuetext', '2 de 5 bloques jugados');
  });

  it.each([
    ['in_progress', inProgress, ['played', 'played', 'current', 'pending', 'pending']],
    ['finished', finished, ['played', 'played', 'played', 'played', 'played']],
    ['sacked', sacked, ['played', 'played', 'sacked', 'pending', 'pending']],
  ] as const)('draws one segment per block when %s', (status, progress, expected) => {
    const { container } = render(<BlockProgress progress={progress} status={status} />);

    expect(segmentStates(container)).toEqual(expected);
  });

  it.each<[RunStatus, SeasonProgress]>([
    ['in_progress', inProgress],
    ['finished', finished],
    ['sacked', sacked],
  ])('has no accessibility violations when %s', async (status, progress) => {
    const { container } = render(<BlockProgress progress={progress} status={status} />);

    expect(await axe(container)).toHaveNoViolations();
  });
});
