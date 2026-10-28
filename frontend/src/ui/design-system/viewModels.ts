/**
 * Data shapes the components accept. Field names and values mirror the frontend view
 * models of T4.3 (`MatchResultViewModel`, `PositionChangeViewModel`,
 * `SeasonProgressViewModel`), so a view model can be passed straight in; the design
 * system never builds them.
 */
export type MatchOutcome = 'win' | 'draw' | 'loss';

export interface MatchLineResult {
  homeName: string;
  awayName: string;
  homeScore: number;
  awayScore: number;
  /** For example «tras la prórroga» or «4-3 en los penaltis». */
  detailText: string | null;
  outcome: MatchOutcome;
  outcomeLabel: string;
}

export type PositionDirection = 'up' | 'down' | 'same' | 'new';

export interface PositionChange {
  direction: PositionDirection;
  /** Short visual mark such as «▲2»; null when there is no previous position. */
  symbol: string | null;
  /** Spoken version such as «Sube 2 puestos». */
  text: string | null;
}

export type RunStatus = 'in_progress' | 'finished' | 'sacked';

export interface SeasonProgress {
  blockNumber: number;
  totalBlocks: number;
  playedBlocks: number;
  percent: number;
  isOver: boolean;
  title: string;
  subtitle: string;
}

export interface TeamColors {
  primary: string;
  secondary: string;
}
