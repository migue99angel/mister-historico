import { describe, expect, it } from 'vitest';

import * as runResultModule from '.';

describe('RunResult public entry point', () => {
  it('exposes the screen and the terminal run guard for the final route', () => {
    expect(Object.keys(runResultModule).sort()).toEqual(['RunResult', 'isTerminalRun']);
  });
});
