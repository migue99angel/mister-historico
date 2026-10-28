/**
 * Synthetic showcase data: Test FC, the Liga Test and invented rivals. Never real
 * historical data (CLAUDE.md); names and colours follow the MSW fixtures.
 */
import type { DilemmaCardData } from '../DilemmaCard';
import type { MiniStandingsRow } from '../MiniStandings';
import type { MatchLineResult, SeasonProgress, TeamColors } from '../viewModels';

export interface SampleClub {
  name: string;
  colors: TeamColors;
}

export const clubs = {
  testFc: { name: 'Test FC', colors: { primary: '#1d4ed8', secondary: '#f8fafc' } },
  rovers: { name: 'Rovers Prueba', colors: { primary: '#b91c1c', secondary: '#fde68a' } },
  union: { name: 'Union Ficticia', colors: { primary: '#15803d', secondary: '#ffffff' } },
  athletic: { name: 'Athletic Ensayo', colors: { primary: '#7e22ce', secondary: '#f1f5f9' } },
  deportivo: { name: 'Deportivo Muestra', colors: { primary: '#0f766e', secondary: '#fef3c7' } },
  sporting: { name: 'Sporting Maqueta', colors: { primary: '#ea580c', secondary: '#1e293b' } },
  racing: { name: 'Racing Boceto', colors: { primary: '#facc15', secondary: '#0f172a' } },
  ciudad: { name: 'Ciudad Ejemplo CF', colors: { primary: '#0ea5e9', secondary: '#ffffff' } },
} satisfies Record<string, SampleClub>;

export const LEAGUE = 'Liga Test';
export const CUP = 'Copa Test';
export const SEASON_LABEL = '2000-01';
export const HISTORICAL_MANAGER = 'Ramon Prueba';

export const dilemmas: readonly DilemmaCardData[] = [
  {
    id: 'board-meeting',
    title: 'Reunión con la directiva',
    prompt: 'La directiva cuestiona tu plan en público. ¿Cómo respondes?',
    options: [
      { id: 'support-the-board', label: 'Respaldar a la directiva en público' },
      { id: 'confront-the-board', label: 'Plantar cara a la directiva' },
    ],
  },
  {
    id: 'summer-striker',
    title: 'Delantero de verano',
    prompt: 'La directiva te da presupuesto para un delantero. ¿A quién quieres?',
    options: [
      { id: 'sign-the-veteran', label: 'Fichar al delantero veterano' },
      { id: 'promote-the-youth', label: 'Subir al delantero de la cantera' },
      { id: 'keep-the-budget', label: 'Guardar el dinero para invierno' },
    ],
  },
];

/** Dilemmas for the component specimens, distinct from the mock-ups' (unique regions). */
export const specimenDilemmas: readonly DilemmaCardData[] = [
  {
    id: 'captain-complaint',
    title: 'Queja del capitán',
    prompt: 'El capitán quiere opinar sobre la alineación. ¿Qué haces?',
    options: [
      { id: 'listen-to-captain', label: 'Escuchar al capitán' },
      { id: 'impose-authority', label: 'Imponer tu autoridad' },
    ],
  },
  {
    id: 'winter-signing',
    title: 'Fichaje de invierno',
    prompt: 'Hay un centrocampista disponible en el mercado de invierno.',
    options: [
      { id: 'sign-the-midfielder', label: 'Fichar al centrocampista' },
      { id: 'keep-the-squad', label: 'Mantener la plantilla' },
      { id: 'loan-a-youngster', label: 'Ceder a un canterano' },
    ],
  },
];

/** Second synthetic club for the verdict specimens (the mock-ups use Test FC). */
export const ROVERS_HISTORICAL_MANAGER = 'Elena Ensayo';

export interface SampleMatch {
  match: MatchLineResult;
  competitionName: string;
  userSide: 'home' | 'away';
  keyMatchLabel?: string;
}

/** Last block played in the loop mock-up: August, 3 wins, 1 draw and 1 loss. */
export const lastBlockMatches: readonly SampleMatch[] = [
  {
    match: {
      homeName: 'Test FC',
      awayName: 'Rovers Prueba',
      homeScore: 2,
      awayScore: 1,
      detailText: null,
      outcome: 'win',
      outcomeLabel: 'Victoria',
    },
    competitionName: LEAGUE,
    userSide: 'home',
  },
  {
    match: {
      homeName: 'Union Ficticia',
      awayName: 'Test FC',
      homeScore: 1,
      awayScore: 1,
      detailText: null,
      outcome: 'draw',
      outcomeLabel: 'Empate',
    },
    competitionName: LEAGUE,
    userSide: 'away',
  },
  {
    match: {
      homeName: 'Test FC',
      awayName: 'Sporting Maqueta',
      homeScore: 3,
      awayScore: 0,
      detailText: null,
      outcome: 'win',
      outcomeLabel: 'Victoria',
    },
    competitionName: LEAGUE,
    userSide: 'home',
  },
  {
    match: {
      homeName: 'Test FC',
      awayName: 'Athletic Ensayo',
      homeScore: 1,
      awayScore: 1,
      detailText: 'tras la prórroga, 4-3 en los penaltis',
      outcome: 'win',
      outcomeLabel: 'Victoria',
    },
    competitionName: CUP,
    userSide: 'home',
    keyMatchLabel: 'Partido clave',
  },
  {
    match: {
      homeName: 'Deportivo Muestra',
      awayName: 'Test FC',
      homeScore: 2,
      awayScore: 0,
      detailText: null,
      outcome: 'loss',
      outcomeLabel: 'Derrota',
    },
    competitionName: LEAGUE,
    userSide: 'away',
  },
];

export const extraTimeMatch: SampleMatch = {
  match: {
    homeName: 'Racing Boceto',
    awayName: 'Test FC',
    homeScore: 1,
    awayScore: 2,
    detailText: 'tras la prórroga',
    outcome: 'win',
    outcomeLabel: 'Victoria',
  },
  competitionName: CUP,
  userSide: 'away',
};

/** Liga Test after August: Test FC climbs from fifth to second. */
export const standingsAfterAugust: readonly MiniStandingsRow[] = [
  {
    position: 1,
    teamName: 'Union Ficticia',
    played: 4,
    points: 10,
    change: { direction: 'same', symbol: '=', text: 'Mantiene el puesto' },
  },
  {
    position: 2,
    teamName: 'Test FC',
    played: 4,
    points: 7,
    isUser: true,
    change: { direction: 'up', symbol: '▲3', text: 'Sube 3 puestos' },
  },
  {
    position: 3,
    teamName: 'Deportivo Muestra',
    played: 4,
    points: 7,
    change: { direction: 'up', symbol: '▲1', text: 'Sube 1 puesto' },
  },
  {
    position: 4,
    teamName: 'Rovers Prueba',
    played: 4,
    points: 6,
    change: { direction: 'down', symbol: '▼2', text: 'Baja 2 puestos' },
  },
  {
    position: 5,
    teamName: 'Athletic Ensayo',
    played: 4,
    points: 5,
    change: { direction: 'down', symbol: '▼2', text: 'Baja 2 puestos' },
  },
];

export const finalStandings: readonly MiniStandingsRow[] = [
  {
    position: 1,
    teamName: 'Test FC',
    played: 38,
    points: 84,
    isUser: true,
    change: { direction: 'up', symbol: '▲1', text: 'Sube 1 puesto' },
  },
  {
    position: 2,
    teamName: 'Union Ficticia',
    played: 38,
    points: 81,
    change: { direction: 'down', symbol: '▼1', text: 'Baja 1 puesto' },
  },
  {
    position: 3,
    teamName: 'Deportivo Muestra',
    played: 38,
    points: 72,
    change: { direction: 'same', symbol: '=', text: 'Mantiene el puesto' },
  },
  {
    position: 4,
    teamName: 'Rovers Prueba',
    played: 38,
    points: 66,
    change: { direction: 'new', symbol: null, text: null },
  },
];

function progress(overrides: Partial<SeasonProgress>): SeasonProgress {
  return {
    blockNumber: 1,
    totalBlocks: 5,
    playedBlocks: 0,
    percent: 0,
    isOver: false,
    title: 'Bloque 1 de 5',
    subtitle: 'Agosto',
    ...overrides,
  };
}

export const progressStates = {
  start: progress({}),
  loop: progress({
    blockNumber: 2,
    playedBlocks: 1,
    percent: 20,
    title: 'Bloque 2 de 5',
    subtitle: 'Octubre-noviembre',
  }),
  middle: progress({
    blockNumber: 3,
    playedBlocks: 2,
    percent: 40,
    title: 'Bloque 3 de 5',
    subtitle: 'Diciembre-enero',
  }),
  finished: progress({
    blockNumber: 5,
    playedBlocks: 5,
    percent: 100,
    isOver: true,
    title: 'Temporada terminada',
    subtitle: 'Abril-mayo',
  }),
  sacked: progress({
    blockNumber: 3,
    playedBlocks: 3,
    percent: 60,
    isOver: true,
    title: 'Destituido en el bloque 3 de 5',
    subtitle: 'Diciembre-enero',
  }),
};
