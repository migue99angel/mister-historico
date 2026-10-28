import { cx } from './styles';
import type { MatchLineResult, MatchOutcome } from './viewModels';

export interface MatchLineProps {
  match: MatchLineResult;
  competitionName?: string | undefined;
  keyMatchLabel?: string | null | undefined;
  /** Side of the player's team, shown in bold. */
  userSide?: 'home' | 'away' | undefined;
}

const OUTCOME_BADGES: Record<MatchOutcome, { letter: string; className: string }> = {
  win: { letter: 'V', className: 'bg-win text-on-accent' },
  draw: { letter: 'E', className: 'bg-draw text-on-accent' },
  loss: { letter: 'D', className: 'bg-loss text-on-accent' },
};

export function MatchLine({ match, competitionName, keyMatchLabel, userSide }: MatchLineProps) {
  const badge = OUTCOME_BADGES[match.outcome];
  const meta = [competitionName, match.detailText].filter(Boolean);

  return (
    <div className="flex items-center gap-3 py-2">
      <span
        aria-hidden="true"
        className={cx(
          'grid size-7 shrink-0 place-items-center rounded-md text-caption font-bold',
          badge.className,
        )}
      >
        {badge.letter}
      </span>
      <span className="sr-only">{match.outcomeLabel}</span>
      <div className="min-w-0 flex-1">
        <p className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-body text-ink">
          <span
            className={cx(
              'text-right leading-tight break-words',
              userSide === 'home' && 'font-bold',
            )}
          >
            {match.homeName}
          </span>
          <span className="rounded-md bg-surface-raised px-2 font-display font-bold tabular-nums">
            {`${String(match.homeScore)}–${String(match.awayScore)}`}
          </span>
          <span className={cx('leading-tight break-words', userSide === 'away' && 'font-bold')}>
            {match.awayName}
          </span>
        </p>
        {(meta.length > 0 || keyMatchLabel) && (
          <p className="mt-0.5 flex flex-wrap items-center justify-center gap-x-2 text-caption text-ink-muted">
            {keyMatchLabel && (
              <span className="rounded-full border border-gold/60 px-2 font-semibold text-gold">
                {keyMatchLabel}
              </span>
            )}
            {meta.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </p>
        )}
      </div>
    </div>
  );
}
