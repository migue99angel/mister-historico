import { cx } from './styles';
import type { PositionChange, PositionDirection } from './viewModels';

export interface MiniStandingsRow {
  position: number;
  teamName: string;
  played: number;
  points: number;
  isUser?: boolean | undefined;
  change?: PositionChange | null | undefined;
}

export interface MiniStandingsProps {
  competitionName: string;
  rows: readonly MiniStandingsRow[];
}

const CHANGE_CLASSES: Record<PositionDirection, string> = {
  up: 'text-win',
  down: 'text-loss',
  same: 'text-ink-muted',
  new: 'text-ink-muted',
};

export function MiniStandings({ competitionName, rows }: MiniStandingsProps) {
  return (
    <table className="w-full border-collapse text-body text-ink">
      <caption className="mb-2 text-left text-caption font-semibold tracking-wide text-ink-muted uppercase">
        {competitionName}
      </caption>
      <thead>
        <tr className="text-caption text-ink-muted">
          <th scope="col" className="w-14 py-1 text-left font-semibold">
            <abbr title="Posición" className="no-underline">
              Pos.
            </abbr>
          </th>
          <th scope="col" className="py-1 text-left font-semibold">
            Equipo
          </th>
          <th scope="col" className="w-10 py-1 text-right font-semibold">
            <abbr title="Partidos jugados" className="no-underline">
              PJ
            </abbr>
          </th>
          <th scope="col" className="w-10 py-1 text-right font-semibold">
            <abbr title="Puntos" className="no-underline">
              Pts
            </abbr>
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.teamName}
            aria-current={row.isUser ? 'true' : undefined}
            className={cx(
              'border-t border-line',
              row.isUser && 'bg-accent/10 font-bold shadow-[inset_3px_0_0] shadow-accent',
            )}
          >
            <td className="py-2 pl-2 tabular-nums">
              {row.position}
              {row.change?.symbol && (
                <span
                  aria-hidden="true"
                  className={cx('ml-1 text-caption', CHANGE_CLASSES[row.change.direction])}
                >
                  {row.change.symbol}
                </span>
              )}
              {row.change?.text && <span className="sr-only">{row.change.text}</span>}
            </td>
            <th
              scope="row"
              className={cx(
                'py-2 pr-2 text-left leading-tight break-words',
                row.isUser ? 'font-bold' : 'font-normal',
              )}
            >
              {row.teamName}
            </th>
            <td className="py-2 text-right tabular-nums">{row.played}</td>
            <td className="py-2 pr-1 text-right font-bold tabular-nums">{row.points}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
