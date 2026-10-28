export type MatchOutcome = 'win' | 'draw' | 'loss';

export type MatchDecidedBy = 'regular_time' | 'extra_time' | 'penalties';

export interface ScoreInput {
  home: number;
  away: number;
}

/** Structural subset of a match report: goals after 90 minutes plus tie-breakers. */
export interface MatchResultInput {
  home: { name: string };
  away: { name: string };
  homeGoals: number;
  awayGoals: number;
  extraTime: ScoreInput | null;
  penalties: ScoreInput | null;
  userResult: MatchOutcome;
}

export interface MatchResultViewModel {
  homeName: string;
  awayName: string;
  homeScore: number;
  awayScore: number;
  decidedBy: MatchDecidedBy;
  scoreText: string;
  detailText: string | null;
  text: string;
  outcome: MatchOutcome;
  outcomeLabel: string;
}

const OUTCOME_LABELS: Record<MatchOutcome, string> = {
  win: 'Victoria',
  draw: 'Empate',
  loss: 'Derrota',
};

export function formatMatchResult(match: MatchResultInput): MatchResultViewModel {
  const homeScore = match.homeGoals + (match.extraTime?.home ?? 0);
  const awayScore = match.awayGoals + (match.extraTime?.away ?? 0);
  const scoreText = `${String(homeScore)}-${String(awayScore)}`;

  let decidedBy: MatchDecidedBy = 'regular_time';
  let detailText: string | null = null;
  if (match.penalties) {
    decidedBy = 'penalties';
    const shootout = `${String(match.penalties.home)}-${String(match.penalties.away)} en los penaltis`;
    detailText = match.extraTime ? `tras la prórroga, ${shootout}` : shootout;
  } else if (match.extraTime) {
    decidedBy = 'extra_time';
    detailText = 'tras la prórroga';
  }

  const baseText = `${match.home.name} ${scoreText} ${match.away.name}`;
  return {
    homeName: match.home.name,
    awayName: match.away.name,
    homeScore,
    awayScore,
    decidedBy,
    scoreText,
    detailText,
    text: detailText ? `${baseText} (${detailText})` : baseText,
    outcome: match.userResult,
    outcomeLabel: OUTCOME_LABELS[match.userResult],
  };
}
