export type RunStatus = 'in_progress' | 'finished' | 'sacked';

/**
 * Structural subset of a run view. `block.number` is the block to play next while the run
 * is in progress, and the last block played once it has ended.
 */
export interface SeasonProgressInput {
  status: RunStatus;
  block: { number: number; total: number; label: string };
}

export interface SeasonProgressViewModel {
  blockNumber: number;
  totalBlocks: number;
  playedBlocks: number;
  percent: number;
  isOver: boolean;
  title: string;
  subtitle: string;
}

export function describeSeasonProgress(run: SeasonProgressInput): SeasonProgressViewModel {
  const { number, total, label } = run.block;
  const isOver = run.status !== 'in_progress';
  const playedBlocks = isOver ? number : number - 1;
  const ofTotal = `${String(number)} de ${String(total)}`;

  let title = `Bloque ${ofTotal}`;
  if (run.status === 'finished') title = 'Temporada terminada';
  if (run.status === 'sacked') title = `Destituido en el bloque ${ofTotal}`;

  return {
    blockNumber: number,
    totalBlocks: total,
    playedBlocks,
    percent: Math.round((playedBlocks / total) * 100),
    isOver,
    title,
    subtitle: label,
  };
}
