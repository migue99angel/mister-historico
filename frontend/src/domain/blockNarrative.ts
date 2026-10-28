import {
  formatMatchResult,
  type MatchOutcome,
  type MatchResultInput,
  type MatchResultViewModel,
} from './matchResult';
import { countable } from './countable';
import { findUserStanding, type StandingsInput, type UserStandingViewModel } from './standings';

/** Structural subset of a match report in a block summary. */
export interface BlockMatchInput extends MatchResultInput {
  competitionName: string;
  isKeyMatch: boolean;
  keyMatchLabel: string | null;
}

/** Structural subset of a block summary. */
export interface BlockSummaryInput {
  label: string;
  results: BlockMatchInput[];
  standings: StandingsInput[];
  events: { date: string; text: string }[];
  injuries: { playerName: string; daysOut: number }[];
}

const RECORD_KEYS: Record<MatchOutcome, keyof BlockRecord> = {
  win: 'won',
  draw: 'drawn',
  loss: 'lost',
};

export type BlockTone = 'positive' | 'neutral' | 'negative';

export interface BlockRecord {
  won: number;
  drawn: number;
  lost: number;
}

export interface KeyMatchViewModel {
  label: string;
  text: string;
}

export interface BlockNarrativeViewModel {
  title: string;
  record: BlockRecord;
  recordText: string;
  tone: BlockTone;
  results: MatchResultViewModel[];
  keyMatches: KeyMatchViewModel[];
  standing: UserStandingViewModel | null;
  events: string[];
  injuries: string[];
}

const SPANISH_LIST = new Intl.ListFormat('es', { type: 'conjunction' });

function recordText(record: BlockRecord): string {
  const parts: string[] = [];
  if (record.won > 0) parts.push(countable(record.won, 'victoria', 'victorias'));
  if (record.drawn > 0) parts.push(countable(record.drawn, 'empate', 'empates'));
  if (record.lost > 0) parts.push(countable(record.lost, 'derrota', 'derrotas'));
  return parts.length === 0 ? 'Sin partidos en este bloque' : SPANISH_LIST.format(parts);
}

function tone(record: BlockRecord): BlockTone {
  if (record.won > record.lost) return 'positive';
  if (record.won < record.lost) return 'negative';
  return 'neutral';
}

export function describeBlock(summary: BlockSummaryInput): BlockNarrativeViewModel {
  const record: BlockRecord = { won: 0, drawn: 0, lost: 0 };
  for (const match of summary.results) record[RECORD_KEYS[match.userResult]] += 1;

  const formatted = summary.results.map((match) => ({ match, view: formatMatchResult(match) }));
  const keyMatches = formatted
    .filter(({ match }) => match.isKeyMatch)
    .map(({ match, view }) => ({
      label: match.keyMatchLabel ?? match.competitionName,
      text: view.text,
    }));

  // ISO dates sort lexicographically; Array.prototype.sort is stable.
  const events = [...summary.events]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((event) => event.text);

  return {
    title: summary.label,
    record,
    recordText: recordText(record),
    tone: tone(record),
    results: formatted.map(({ view }) => view),
    keyMatches,
    standing: findUserStanding(summary.standings),
    events,
    injuries: summary.injuries.map(
      (injury) => `${injury.playerName}: ${countable(injury.daysOut, 'día', 'días')} de baja`,
    ),
  };
}
