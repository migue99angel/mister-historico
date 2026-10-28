import { fireEvent, screen, waitFor } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderWithRuntime,
} from '../../../test/renderWithRuntime';

import { decideBlock, startRunOnDevice } from '../../ui/screens/RunResult/testRuns';
import { AppRoutes } from '../Routes';

// Kept apart from RunFinalRoute.test.tsx: its vi.mock probe replaces the real route for the
// whole file, and this flow needs the real run loop and final screens behind AppRoutes.
describe('From the run loop to the final page', () => {
  it('opens the final page of a sacked run with its title focused and no new fetch', async () => {
    const runtime = createTestRuntime();
    const { gameApi, runTokenStore } = runtime;
    const started = await startRunOnDevice(gameApi, runTokenStore, mockFixtures.TEST_SEASON_ID);
    const { runId } = started.run;
    await decideBlock(gameApi, started, mockFixtures.SACK_OPTION_ID);
    window.history.replaceState(null, '', `/partida/${runId}`);
    const historyLength = window.history.length;
    renderWithRuntime(<AppRoutes />, { runtime });
    const simulate = await screen.findByRole('button', { name: /Simular bloque/ });
    await waitFor(() => {
      expect(simulate).toBeEnabled();
    });
    const runFetches: string[] = [];
    mockServer.use(
      http.get('*/api/runs/:runId', ({ request }) => {
        runFetches.push(request.url);
      }),
    );

    fireEvent.click(simulate);

    const title = await screen.findByRole('heading', { level: 1, name: 'Final de la partida' });
    expect(title).toHaveFocus();
    expect(window.location.pathname).toBe(`/partida/${runId}/final`);
    expect(window.history.length).toBe(historyLength);
    expect(runFetches).toEqual([]);
  });
});
