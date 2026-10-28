import { cx } from './styles';
import type { RunStatus, SeasonProgress } from './viewModels';

export interface BlockProgressProps {
  progress: SeasonProgress;
  /** Defaults to `finished` once the season is over; pass `sacked` to mark the last block. */
  status?: RunStatus;
}

type SegmentState = 'played' | 'current' | 'pending' | 'sacked';

const SEGMENT_CLASSES: Record<SegmentState, string> = {
  played: 'bg-accent',
  current: 'bg-accent/30 ring-2 ring-accent ring-inset motion-safe:animate-pulse',
  pending: 'bg-line',
  sacked: 'bg-loss',
};

function segmentState(index: number, played: number, status: RunStatus): SegmentState {
  if (index < played) return status === 'sacked' && index === played - 1 ? 'sacked' : 'played';
  if (index === played && status === 'in_progress') return 'current';
  return 'pending';
}

export function BlockProgress({
  progress,
  status = progress.isOver ? 'finished' : 'in_progress',
}: BlockProgressProps) {
  const { playedBlocks, totalBlocks } = progress;

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <p
          className={cx(
            'font-display text-title font-bold',
            status === 'sacked' ? 'text-loss' : 'text-ink',
          )}
        >
          {progress.title}
        </p>
        <p className="text-caption text-ink-muted">{progress.subtitle}</p>
      </div>
      <div
        role="progressbar"
        aria-label="Progreso de la temporada"
        aria-valuemin={0}
        aria-valuemax={totalBlocks}
        aria-valuenow={playedBlocks}
        aria-valuetext={`${String(playedBlocks)} de ${String(totalBlocks)} bloques jugados`}
        className="flex gap-1.5"
      >
        {Array.from({ length: totalBlocks }, (_, index) => {
          const state = segmentState(index, playedBlocks, status);
          return (
            <span
              key={index}
              data-segment={state}
              className={cx('h-2.5 flex-1 rounded-full', SEGMENT_CLASSES[state])}
            />
          );
        })}
      </div>
    </div>
  );
}
