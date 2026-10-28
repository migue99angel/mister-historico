import { describe, expect, it } from 'vitest';

import { matchRoute } from './routeMatcher';
import { createRouteNavigation } from './routeNavigation';

function recordNavigation() {
  const calls: { to: string; replace: boolean }[] = [];
  const navigation = createRouteNavigation((to, replace = false) => {
    calls.push({ to, replace });
  });
  return { calls, navigation };
}

describe('createRouteNavigation', () => {
  it('opens the team page of the chosen season', () => {
    const { calls, navigation } = recordNavigation();

    navigation.onSeasonChosen('test-fc-2000-01');

    expect(calls).toEqual([{ to: '/equipo/test-fc-2000-01', replace: false }]);
  });

  it('opens the run page once a run has started', () => {
    const { calls, navigation } = recordNavigation();

    navigation.onRunStarted('run-1');

    expect(calls).toEqual([{ to: '/partida/run-1', replace: false }]);
  });

  it('replaces the finished run loop with its final page so Back does not reopen it', () => {
    const { calls, navigation } = recordNavigation();

    navigation.onRunEnded('run-1');

    expect(calls).toEqual([{ to: '/partida/run-1/final', replace: true }]);
  });

  it('returns home to play again', () => {
    const { calls, navigation } = recordNavigation();

    navigation.onPlayAgain();

    expect(calls).toEqual([{ to: '/', replace: false }]);
  });

  it('encodes identifiers so the route matcher reads them back unchanged', () => {
    const { calls, navigation } = recordNavigation();

    navigation.onSeasonChosen('test fc/2000');
    navigation.onRunStarted('run ?1');
    navigation.onRunEnded('run#1');

    expect(calls.map((call) => matchRoute(call.to))).toEqual([
      { kind: 'season', seasonId: 'test fc/2000' },
      { kind: 'run', runId: 'run ?1' },
      { kind: 'run-final', runId: 'run#1' },
    ]);
  });
});
