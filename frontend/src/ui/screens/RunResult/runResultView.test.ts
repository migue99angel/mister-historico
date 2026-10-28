import { describe, expect, it } from 'vitest';

import type { RunStatusDto } from '../../../application/ports';
import { isTerminalRun } from './runResultView';

describe('isTerminalRun', () => {
  it.each<[RunStatusDto, boolean]>([
    ['finished', true],
    ['sacked', true],
    ['in_progress', false],
  ])('treats a %s run as terminal: %s', (status, expected) => {
    expect(isTerminalRun({ status })).toBe(expected);
  });
});
