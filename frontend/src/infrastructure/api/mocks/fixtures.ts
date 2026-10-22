import type { components } from '../generated/schema';

/**
 * Fictional Test FC data for the MSW handlers. Nothing here is real: names, clubs and results
 * are invented, in line with the project rule of never using historical data in app tests.
 */

type Schemas = components['schemas'];

export const TEST_SEASON_ID = 'test-fc-2000-01';
export const ROVERS_SEASON_ID = 'test-rovers-2001-02';
/** Option that wrecks the board confidence and gets the manager sacked on the next advance. */
export const SACK_OPTION_ID = 'confront-the-board';
/** Board confidence under this value after a block gets the manager sacked. */
export const SACK_THRESHOLD = 30;

const KEY_PLAYERS: Schemas['PlayerSummary'][] = [
  {
    id: 'ivan-delantero',
    displayName: 'Ivan Delantero',
    position: 'forward',
    age: 27,
    rating: 84,
    key: true,
  },
  {
    id: 'marco-medio',
    displayName: 'Marco Medio',
    position: 'midfielder',
    age: 30,
    rating: 79,
    key: true,
  },
  {
    id: 'pablo-portero',
    displayName: 'Pablo Portero',
    position: 'goalkeeper',
    age: 33,
    rating: 77,
    key: true,
  },
];

export const SEASON_DETAILS: Schemas['SeasonDetail'][] = [
  {
    id: TEST_SEASON_ID,
    clubName: 'Test FC',
    shortName: 'TFC',
    seasonLabel: '2000-01',
    historicalManager: 'Ramon Prueba',
    colors: { primary: '#1d4ed8', secondary: '#f8fafc' },
    presentation: 'The board hires you after a mid-table finish. The fans want a title.',
    boardObjectives: [
      {
        id: 'finish-top-four',
        description: 'Finish the league in the top four.',
        competitionId: 'liga-test',
      },
      {
        id: 'reach-cup-semis',
        description: 'Reach the semi-finals of the cup.',
        competitionId: 'copa-test',
      },
    ],
    squad: { size: 22, averageRating: 74.5, keyPlayers: KEY_PLAYERS },
    competitions: [
      { id: 'liga-test', name: 'Liga Test', kind: 'league' },
      { id: 'copa-test', name: 'Copa Test', kind: 'cup' },
    ],
    blockCount: 5,
  },
  {
    id: ROVERS_SEASON_ID,
    clubName: 'Rovers Prueba',
    shortName: 'ROV',
    seasonLabel: '2001-02',
    historicalManager: 'Elena Ensayo',
    colors: { primary: '#b91c1c', secondary: '#fde68a' },
    presentation: 'A proud club coming off a relegation scare. Stay calm and rebuild.',
    boardObjectives: [
      {
        id: 'avoid-relegation',
        description: 'Stay clear of the relegation zone.',
        competitionId: 'liga-test',
      },
    ],
    squad: { size: 21, averageRating: 70, keyPlayers: KEY_PLAYERS.slice(0, 2) },
    competitions: [{ id: 'liga-test', name: 'Liga Test', kind: 'league' }],
    blockCount: 5,
  },
];

export interface OptionDef {
  option: Schemas['DilemmaOption'];
  /** Hidden effects, never exposed through the API. */
  effects: { morale: number; boardConfidence: number };
}

export interface DilemmaDef {
  id: string;
  category: Schemas['DilemmaCategory'];
  prompt: string;
  options: OptionDef[];
}

function dilemma(
  id: string,
  category: Schemas['DilemmaCategory'],
  prompt: string,
  options: [string, string, number, number][],
): DilemmaDef {
  return {
    id,
    category,
    prompt,
    options: options.map(([optionId, label, morale, boardConfidence]) => ({
      option: { id: optionId, label },
      effects: { morale, boardConfidence },
    })),
  };
}

/** Dilemmas of each block, indexed by zero-based block. */
export const DILEMMAS_BY_BLOCK: DilemmaDef[][] = [
  [
    dilemma('board-meeting', 'dressing_room', 'The board questions your plan. How do you answer?', [
      ['support-the-board', 'Back the board in public', 0, 5],
      [SACK_OPTION_ID, 'Publicly confront the board', 10, -45],
    ]),
    dilemma(
      'summer-striker',
      'market',
      'The board offers a budget for one striker. Who do you want?',
      [
        ['sign-the-veteran', 'Sign the veteran striker', 5, 0],
        ['promote-the-youth', 'Promote the academy striker', 0, 5],
      ],
    ),
  ],
  [
    dilemma('captain-complaint', 'dressing_room', 'The captain wants more say in the line-up.', [
      ['listen-to-captain', 'Listen to the captain', 8, -2],
      ['impose-authority', 'Impose your authority', -5, 3],
    ]),
  ],
  [
    dilemma('winter-signing', 'market', 'A midfielder is available in the winter window.', [
      ['sign-the-midfielder', 'Sign the midfielder', 4, 2],
      ['keep-the-squad', 'Keep the current squad', 2, 0],
    ]),
  ],
  [
    dilemma('tactical-style', 'tactics', 'Your side is predictable. Change the style?', [
      ['press-high', 'Press high', 3, 2],
      ['counter-attack', 'Play on the counter', 1, 3],
    ]),
  ],
  [
    dilemma('final-rotation', 'rotation', 'A cup final is close and the squad is tired.', [
      ['rotate-the-squad', 'Rotate the squad', -2, 1],
      ['play-the-best-eleven', 'Play the best eleven', 4, 2],
    ]),
  ],
];

export const BLOCK_LABELS = [
  'August',
  'October-November',
  'December-January',
  'February-March',
  'April-May',
];
/** Calendar month in which each block ends (used as the sacking month). */
export const BLOCK_END_MONTH = [9, 11, 1, 3, 5];
const BLOCK_DATES = ['2000-09-16', '2000-11-18', '2001-01-20', '2001-03-17', '2001-05-19'];

function team(name: string, isUser = false): Schemas['TeamRef'] {
  return { name, isUser };
}

/** Matches of each block. Block 3 has an extra-time cup tie and block 4 a shoot-out. */
export function resultsForBlock(block: number): Schemas['MatchReport'][] {
  const date = BLOCK_DATES[block] ?? '2001-05-19';
  const league: Schemas['MatchReport'] = {
    fixtureId: `tfc-rovers-block-${String(block + 1)}`,
    competitionId: 'liga-test',
    competitionName: 'Liga Test',
    round: `Matchday ${String((block + 1) * 4)}`,
    date,
    home: team('Test FC', true),
    away: team('Rovers Prueba'),
    homeGoals: 2,
    awayGoals: 1,
    extraTime: null,
    penalties: null,
    isKeyMatch: block % 2 === 0,
    keyMatchLabel: block % 2 === 0 ? 'Derby' : null,
    userResult: 'win',
  };
  const draw: Schemas['MatchReport'] = {
    ...league,
    fixtureId: `united-tfc-block-${String(block + 1)}`,
    round: `Matchday ${String((block + 1) * 4 + 1)}`,
    home: team('Union Ficticia'),
    away: team('Test FC', true),
    homeGoals: 1,
    awayGoals: 1,
    isKeyMatch: false,
    keyMatchLabel: null,
    userResult: 'draw',
  };
  if (block === 2) {
    return [
      league,
      draw,
      {
        ...league,
        fixtureId: 'copa-test-quarter-final',
        competitionId: 'copa-test',
        competitionName: 'Copa Test',
        round: 'Quarter-final',
        homeGoals: 1,
        awayGoals: 1,
        extraTime: { home: 1, away: 0 },
        isKeyMatch: true,
        keyMatchLabel: 'Knockout tie',
      },
    ];
  }
  if (block === 3) {
    return [
      league,
      draw,
      {
        ...league,
        fixtureId: 'copa-test-semi-final',
        competitionId: 'copa-test',
        competitionName: 'Copa Test',
        round: 'Semi-final',
        home: team('Athletic Ensayo'),
        away: team('Test FC', true),
        homeGoals: 0,
        awayGoals: 0,
        extraTime: { home: 0, away: 0 },
        penalties: { home: 3, away: 4 },
        isKeyMatch: true,
        keyMatchLabel: 'Knockout tie',
      },
    ];
  }
  return [league, draw];
}

export function standingsForBlock(block: number): Schemas['Standings'] {
  const played = (block + 1) * 4;
  const userPoints = played * 2 + 1;
  const rows: Schemas['StandingRow'][] = [
    ['Test FC', true, userPoints],
    ['Rovers Prueba', false, userPoints - 2],
    ['Union Ficticia', false, userPoints - 4],
    ['Athletic Ensayo', false, userPoints - 7],
  ].map(([name, isUser, points], index) => {
    const pts = points as number;
    const won = Math.floor(pts / 3);
    return {
      position: index + 1,
      previousPosition: block === 0 ? null : index + 1,
      team: team(name as string, isUser as boolean),
      played,
      won,
      drawn: pts - won * 3,
      lost: Math.max(played - won - (pts - won * 3), 0),
      goalsFor: won * 2 + 3,
      goalsAgainst: Math.max(played - won, 1),
      points: pts,
    };
  });
  return { competitionId: 'liga-test', competitionName: 'Liga Test', rows };
}

export function eventsForBlock(block: number): Schemas['BlockEvent'][] {
  return [
    {
      kind: 'milestone',
      date: BLOCK_DATES[block] ?? '2001-05-19',
      text: `Test FC closes block ${String(block + 1)} among the leaders.`,
    },
  ];
}

/** Block in which Ivan Delantero picks up an injury. */
export const INJURY_BLOCK = 1;

export function injuriesForBlock(block: number): Schemas['InjuryReport'][] {
  return block === INJURY_BLOCK
    ? [
        {
          playerId: 'ivan-delantero',
          playerName: 'Ivan Delantero',
          date: '2000-11-02',
          daysOut: 14,
        },
      ]
    : [];
}

export const SQUAD_PLAYERS = KEY_PLAYERS;

export interface SeededEntry {
  runId: string;
  alias: string;
  misterScore: number;
  verdictKind: Schemas['VerdictKind'];
  finishedAt: string;
}

/** Fictional leaderboard entries present before any run is played. */
export const SEEDED_LEADERBOARD: SeededEntry[] = [
  {
    runId: '11111111-1111-4111-8111-111111111111',
    alias: 'Entrenador Uno',
    misterScore: 91,
    verdictKind: 'surpassed_history',
    finishedAt: '2026-10-20T18:00:00Z',
  },
  {
    runId: '22222222-2222-4222-8222-222222222222',
    alias: 'Mister Dos',
    misterScore: 66,
    verdictKind: 'matched_history',
    finishedAt: '2026-10-21T09:30:00Z',
  },
  {
    runId: '33333333-3333-4333-8333-333333333333',
    alias: 'Tactico Tres',
    misterScore: 41,
    verdictKind: 'below_history',
    finishedAt: '2026-10-21T21:10:00Z',
  },
];
