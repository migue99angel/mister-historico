export type SlugDto = string;

export interface TeamColorsDto {
  primary: string;
  secondary: string;
}

export interface SeasonSummaryDto {
  id: SlugDto;
  clubName: string;
  shortName: string;
  seasonLabel: string;
  historicalManager: string;
  colors: TeamColorsDto;
}

export interface SeasonListDto {
  items: SeasonSummaryDto[];
}

export interface BoardObjectiveDto {
  id: SlugDto;
  description: string;
  competitionId?: SlugDto | null;
}

export type CompetitionKindDto = 'league' | 'cup' | 'super_cup' | 'continental_cup';
export type CompetitionTierDto =
  | 'domestic_league'
  | 'domestic_cup'
  | 'domestic_super_cup'
  | 'continental_primary'
  | 'continental_secondary';

export interface CompetitionDto {
  id: SlugDto;
  name: string;
  kind: CompetitionKindDto;
  tier: CompetitionTierDto;
}

export type PlayerPositionDto = 'GK' | 'DF' | 'MF' | 'FW';

export interface PlayerSummaryDto {
  id: SlugDto;
  displayName: string;
  position: PlayerPositionDto;
  age: number;
  rating: number;
  key: boolean;
}

export interface SquadOverviewDto {
  size: number;
  averageRating: number;
  keyPlayers: PlayerSummaryDto[];
}

export interface SeasonDetailDto {
  id: SlugDto;
  clubName: string;
  shortName: string;
  seasonLabel: string;
  historicalManager: string;
  colors: TeamColorsDto;
  presentation: string;
  boardObjectives: BoardObjectiveDto[];
  squad: SquadOverviewDto;
  competitions: CompetitionDto[];
  blockCount: number;
}

export interface StartRunRequestDto {
  seasonId: SlugDto;
}

export interface StartRunResponseDto {
  runToken: string;
  run: RunViewDto;
}

export interface TakeDecisionRequestDto {
  dilemmaId: SlugDto;
  optionId: SlugDto;
  expectedVersion: number;
}

export interface AdvanceBlockRequestDto {
  expectedVersion: number;
}

export type RunStatusDto = 'in_progress' | 'finished' | 'sacked';

export interface BlockProgressDto {
  number: number;
  total: number;
  label: string;
}

export interface DilemmaOptionDto {
  id: SlugDto;
  label: string;
}

export interface DilemmaDto {
  id: SlugDto;
  title: string;
  prompt: string;
  options: DilemmaOptionDto[];
}

export interface DecisionDto {
  dilemmaId: SlugDto;
  optionId: SlugDto;
  blockNumber: number;
}

export interface TeamStateDto {
  morale: number;
  boardConfidence: number;
  fitness: number;
}

export interface InjuryStatusDto {
  daysOut: number;
}

export interface SquadMemberDto {
  id: SlugDto;
  displayName: string;
  position: PlayerPositionDto;
  age: number;
  rating: number;
  key: boolean;
  morale: number;
  fitness: number;
  injury: InjuryStatusDto | null;
}

export interface SquadStatusDto {
  size: number;
  averageRating: number;
  players: SquadMemberDto[];
}

export type TacticStyleDto = 'pressing' | 'counter' | 'possession' | 'balanced';

export interface TacticDto {
  style: TacticStyleDto;
  system: string;
}

export type CompetitionPriorityLevelDto = 'low' | 'normal' | 'high';

export interface CompetitionPriorityDto {
  competitionId: SlugDto;
  priority: CompetitionPriorityLevelDto;
}

export interface TeamRefDto {
  clubSeasonId: string;
  name: string;
  shortName: string;
  colors: TeamColorsDto;
  isUser: boolean;
}

export interface ScoreDto {
  home: number;
  away: number;
}

export type VenueDto = 'home' | 'away' | 'neutral';

export interface MatchReportDto {
  fixtureId: SlugDto;
  competitionId: SlugDto;
  competitionName: string;
  round?: string;
  date: string;
  home: TeamRefDto;
  away: TeamRefDto;
  homeGoals: number;
  awayGoals: number;
  extraTime: ScoreDto | null;
  penalties: ScoreDto | null;
  venue: VenueDto;
  isKeyMatch: boolean;
  keyMatchLabel: string | null;
  userResult: 'win' | 'draw' | 'loss';
}

export interface StandingRowDto {
  position: number;
  previousPosition?: number | null;
  team: TeamRefDto;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goalsFor: number;
  goalsAgainst: number;
  points: number;
}

export interface StandingsDto {
  competitionId: SlugDto;
  competitionName: string;
  stageId?: SlugDto;
  groupId?: SlugDto;
  rows: StandingRowDto[];
}

export interface BlockEventDto {
  kind: 'transfer' | 'dressing_room' | 'press' | 'board' | 'milestone';
  date: string;
  text: string;
}

export interface InjuryReportDto {
  playerId: SlugDto;
  playerName: string;
  date: string;
  daysOut: number;
}

export interface BlockSummaryDto {
  blockNumber: number;
  label: string;
  results: MatchReportDto[];
  standings: StandingsDto[];
  events: BlockEventDto[];
  injuries: InjuryReportDto[];
}

export interface RunViewDto {
  runId: string;
  seasonId: SlugDto;
  status: RunStatusDto;
  version: number;
  block: BlockProgressDto;
  pendingDilemmas: DilemmaDto[];
  decisions: DecisionDto[];
  state: TeamStateDto;
  squad: SquadStatusDto;
  tactic: TacticDto;
  competitionPriorities: CompetitionPriorityDto[];
  lastBlockSummary: BlockSummaryDto | null;
  sackedMonth: number | null;
}

export interface RunCredentials {
  runId: string;
  runToken: string;
}

export interface IdempotentRunCommand extends RunCredentials {
  idempotencyKey: string;
}

/** Every operation rejects with `ApiError` (`./apiError`), part of this port's contract. */
export interface GameApi {
  listSeasons(): Promise<SeasonListDto>;
  getSeason(seasonId: string): Promise<SeasonDetailDto>;
  startRun(request: StartRunRequestDto): Promise<StartRunResponseDto>;
  getRun(runId: string, runToken: string): Promise<RunViewDto>;
  takeDecision(request: IdempotentRunCommand & TakeDecisionRequestDto): Promise<RunViewDto>;
  advanceBlock(request: IdempotentRunCommand & AdvanceBlockRequestDto): Promise<RunViewDto>;
}

/**
 * Keeps the bearer token `startRun` issues, per run, so a reload can resume the run.
 * Synchronous on purpose: browser storage is synchronous and screens read it while rendering.
 */
export interface RunTokenStore {
  save(runId: string, runToken: string): void;
  /** Returns `null` when no token is known for the run (or storage is unavailable). */
  read(runId: string): string | null;
}
