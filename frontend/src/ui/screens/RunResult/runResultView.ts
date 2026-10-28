import type {
  BlockSummaryDto,
  MatchReportDto,
  RunStatusDto,
  RunViewDto,
  StandingsDto,
  TeamRefDto,
} from '../../../application/ports';
import type { MatchResultViewModel } from '../../../domain/matchResult';
import { toRunViewModel } from '../../../domain/runViewModel';
import type { SeasonProgressViewModel } from '../../../domain/seasonProgress';
import { describePositionChange, type PositionChangeViewModel } from '../../../domain/standings';

export type TerminalStatus = Exclude<RunStatusDto, 'in_progress'>;

/** A run the final screen can show: it has ended, finished or with the manager sacked. */
export type TerminalRunView = RunViewDto & { status: TerminalStatus };

export function isTerminalRun<T extends { status: RunStatusDto }>(
  run: T,
): run is T & { status: TerminalStatus } {
  return run.status !== 'in_progress';
}

export interface ResultMatchView {
  key: string;
  match: MatchResultViewModel;
  competitionName: string;
  keyMatchLabel: string | null;
  userSide: 'home' | 'away' | undefined;
}

export interface ResultStandingRowView {
  position: number;
  teamName: string;
  played: number;
  points: number;
  isUser: boolean;
  change: PositionChangeViewModel;
}

export interface RunResultView {
  /** The user's club, from the last block; null when the run has no summary. */
  club: { name: string; colors: TeamRefDto['colors'] } | null;
  status: TerminalStatus;
  progress: SeasonProgressViewModel;
  outcomeText: string;
  lastBlock: { eyebrow: string; matches: ResultMatchView[] } | null;
  standings: { title: string; competitionName: string; rows: ResultStandingRowView[] } | null;
}

const MONTH_FORMAT = new Intl.DateTimeFormat('es', { month: 'long', timeZone: 'UTC' });

function monthName(month: number): string {
  return MONTH_FORMAT.format(new Date(Date.UTC(2000, month - 1, 1)));
}

function outcomeText(run: TerminalRunView): string {
  if (run.status === 'finished') return 'Has llegado al final de la temporada.';
  if (run.sackedMonth === null) return 'La directiva te destituyó.';
  return `La directiva te destituyó en ${monthName(run.sackedMonth)}.`;
}

function userSide(match: MatchReportDto): 'home' | 'away' | undefined {
  if (match.home.isUser) return 'home';
  if (match.away.isUser) return 'away';
  return undefined;
}

function userTeam(summary: BlockSummaryDto): TeamRefDto | null {
  const teams = [
    ...summary.results.flatMap((report) => [report.home, report.away]),
    ...summary.standings.flatMap((table) => table.rows.map((row) => row.team)),
  ];
  return teams.find((team) => team.isUser) ?? null;
}

/** The user's league table wins over a group-stage table, as in `findUserStanding`. */
function userTable(tables: StandingsDto[]): StandingsDto | null {
  const withUser = tables.filter((table) => table.rows.some((row) => row.team.isUser));
  return withUser.find((table) => table.stageId === undefined) ?? withUser[0] ?? null;
}

/** Decides what the final screen shows for an ended run, from the run view alone. */
export function describeRunResult(run: TerminalRunView): RunResultView {
  const summary = run.lastBlockSummary;
  const { progress, lastBlock } = toRunViewModel(run);
  const table = summary ? userTable(summary.standings) : null;
  const team = summary ? userTeam(summary) : null;

  return {
    club: team && { name: team.name, colors: team.colors },
    status: run.status,
    progress,
    outcomeText: outcomeText(run),
    lastBlock: summary &&
      lastBlock && {
        eyebrow: `${lastBlock.title} · ${lastBlock.recordText}`,
        // The block view model formats each report in order; pair them back by index.
        matches: summary.results.flatMap((report, index) => {
          const match = lastBlock.results[index];
          if (!match) return [];
          return [
            {
              key: report.fixtureId,
              match,
              competitionName: report.competitionName,
              keyMatchLabel: report.keyMatchLabel,
              userSide: userSide(report),
            },
          ];
        }),
      },
    standings: table && {
      title: run.status === 'finished' ? 'Clasificación final' : 'Clasificación en la destitución',
      competitionName: table.competitionName,
      rows: table.rows.map((row) => ({
        position: row.position,
        teamName: row.team.name,
        played: row.played,
        points: row.points,
        isUser: row.team.isUser,
        change: describePositionChange(row),
      })),
    },
  };
}
