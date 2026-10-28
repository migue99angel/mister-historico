/**
 * Design tokens of Míster Histórico. theme.css declares the same values for Tailwind
 * (`bg-surface`, `text-title`, `min-h-touch`…); tokens.test.ts keeps both in sync.
 */
export const colors = {
  canvas: '#0b1210',
  surface: '#131f1a',
  'surface-raised': '#1c2b25',
  line: '#2e4339',
  ink: '#f3f6f1',
  'ink-muted': '#a9b8b0',
  accent: '#3ccb7f',
  'accent-strong': '#6ee0a2',
  'on-accent': '#04120b',
  gold: '#f4c95d',
  'on-gold': '#1d1503',
  win: '#4ad98d',
  draw: '#c5cec8',
  loss: '#ff8a80',
} as const;

export type ColorToken = keyof typeof colors;

export interface TypeStep {
  token: string;
  size: string;
  lineHeight: string;
  usage: string;
}

export const typeScale: readonly TypeStep[] = [
  { token: 'display', size: '2.5rem', lineHeight: '1.05', usage: 'Veredicto y cifras grandes' },
  { token: 'headline', size: '1.75rem', lineHeight: '1.15', usage: 'Título de pantalla' },
  { token: 'title', size: '1.25rem', lineHeight: '1.3', usage: 'Título de tarjeta y dilema' },
  { token: 'body', size: '1rem', lineHeight: '1.5', usage: 'Texto y opciones' },
  { token: 'caption', size: '0.8125rem', lineHeight: '1.35', usage: 'Etiquetas y datos' },
];

export const spacing = {
  touch: '2.75rem',
  gutter: '1rem',
} as const;

/** Minimum size of anything the player taps (WCAG 2.5.5 and platform guidelines). */
export const MIN_TOUCH_TARGET_PX = 44;

export interface TextPair {
  foreground: ColorToken;
  background: ColorToken;
}

/** Every text colour the components put on each background. */
export const textPairs: readonly TextPair[] = [
  ...(['canvas', 'surface', 'surface-raised'] as const).flatMap((background) =>
    (['ink', 'ink-muted', 'accent', 'gold', 'win', 'draw', 'loss'] as const).map((foreground) => ({
      foreground,
      background,
    })),
  ),
  ...(['accent', 'accent-strong', 'win', 'draw', 'loss'] as const).map((background) => ({
    foreground: 'on-accent' as const,
    background,
  })),
  { foreground: 'on-gold', background: 'gold' },
];
