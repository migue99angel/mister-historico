import { describe, expect, it } from 'vitest';

import * as runResultModule from '.';

describe('RunResult public entry point', () => {
  it('exposes the final screen container, the screen and the terminal run guard', () => {
    expect(Object.keys(runResultModule).sort()).toEqual(['RunFinal', 'RunResult', 'isTerminalRun']);
  });
});
