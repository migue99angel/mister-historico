/** Structural subset of a standings row; `previousPosition` is absent or null in the first block. */
export interface StandingRowInput {
  position: number;
  previousPosition?: number | null;
  team: { isUser: boolean };
}

export interface StandingsInput {
  competitionName: string;
  rows: StandingRowInput[];
}

export type PositionDirection = 'up' | 'down' | 'same' | 'new';

export interface PositionChangeViewModel {
  position: number;
  direction: PositionDirection;
  places: number;
  symbol: string | null;
  text: string | null;
}

export interface UserStandingViewModel {
  competitionName: string;
  change: PositionChangeViewModel;
}

function placesText(places: number): string {
  return places === 1 ? '1 puesto' : `${String(places)} puestos`;
}

export function describePositionChange(row: StandingRowInput): PositionChangeViewModel {
  const { position, previousPosition } = row;
  if (previousPosition === undefined || previousPosition === null) {
    return { position, direction: 'new', places: 0, symbol: null, text: null };
  }
  if (position < previousPosition) {
    const places = previousPosition - position;
    return {
      position,
      direction: 'up',
      places,
      symbol: `▲${String(places)}`,
      text: `Sube ${placesText(places)}`,
    };
  }
  if (position > previousPosition) {
    const places = position - previousPosition;
    return {
      position,
      direction: 'down',
      places,
      symbol: `▼${String(places)}`,
      text: `Baja ${placesText(places)}`,
    };
  }
  return { position, direction: 'same', places: 0, symbol: '=', text: 'Mantiene el puesto' };
}

export function findUserStanding(tables: StandingsInput[]): UserStandingViewModel | null {
  for (const table of tables) {
    const userRow = table.rows.find((row) => row.team.isUser);
    if (userRow) {
      return { competitionName: table.competitionName, change: describePositionChange(userRow) };
    }
  }
  return null;
}
