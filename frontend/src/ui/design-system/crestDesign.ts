import { normaliseHex } from './color';
import type { TeamColors } from './viewModels';

export const CREST_SHAPES = ['shield', 'round', 'peaked'] as const;
export const CREST_PATTERNS = [
  'band',
  'stripes',
  'halves',
  'sash',
  'chevron',
  'quarters',
  'hoops',
  'pale',
] as const;

export type CrestShape = (typeof CREST_SHAPES)[number];
export type CrestPattern = (typeof CREST_PATTERNS)[number];

export interface CrestDesign {
  shape: CrestShape;
  pattern: CrestPattern;
  /** Background colour (the club's primary). */
  field: string;
  /** Pattern and rim colour (the club's secondary). */
  charge: string;
}

/** 32-bit FNV-1a: tiny, stable across platforms and good enough to spread designs. */
function fnv1a(text: string): number {
  let hash = 0x811c9dc5;
  for (const char of text) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash;
}

/** Picks a generic crest from the club colours alone: same colours, same crest. */
export function crestDesign(colors: TeamColors): CrestDesign {
  const field = normaliseHex(colors.primary);
  const charge = normaliseHex(colors.secondary);
  const hash = fnv1a(`${field}|${charge}`);

  return {
    shape: CREST_SHAPES[hash % CREST_SHAPES.length] ?? 'shield',
    pattern: CREST_PATTERNS[(hash >>> 8) % CREST_PATTERNS.length] ?? 'band',
    field,
    charge,
  };
}
