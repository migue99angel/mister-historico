import { fireEvent, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { HttpResponse, http } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderWithRuntime,
  type TestRuntime,
} from '../../../../test/renderWithRuntime';
import type { GameApi, RunViewDto } from '../../../application/ports';
import { runQueryKey } from '../../../application/useRun';
import { RunFinal } from './RunFinal';

const UNKNOWN_RUN_ID = '00000000-0000-4000-8000-000000000000';
const UNAVAILABLE = 'Esta partida no está disponible en este dispositivo.';

interface SeededRun {
  runtime: TestRuntime;
  run: RunViewDto;
}

/**
 * Plays a Test FC run through the MSW handlers until it ends, taking each dilemma's first
 * option, or the option that gets the manager sacked when `sack` is set.
 */
async function playUntilEnd(gameApi: GameApi, runId: string, runToken: string, sack: boolean) {
  let run = await gameApi.getRun(runId, runToken);
  for (let block = 0; run.status === 'in_progress'; block += 1) {
    for (const dilemma of run.pendingDilemmas) {
      const sackOption = dilemma.options.find(
        (option) => option.id === mockFixtures.SACK_OPTION_ID,
      );
      const option = sack && sackOption ? sackOption : dilemma.options[0];
      run = await gameApi.takeDecision({
        runId,
        runToken,
        idempotencyKey: `seed-${dilemma.id}`,
        dilemmaId: dilemma.id,
        optionId: option?.id ?? '',
        expectedVersion: run.version,
      });
    }
    run = await gameApi.advanceBlock({
      runId,
      runToken,
      idempotencyKey: `seed-advance-${String(block)}`,
      expectedVersion: run.version,
    });
  }
  return run;
}

/** Starts a run on this device (token in the store) and, unless `ending` is null, ends it. */
async function seedRun(ending: 'finished' | 'sacked' | null): Promise<SeededRun> {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  const { runId } = started.run;
  runtime.runTokenStore.save(runId, started.runToken);
  const run =
    ending === null
      ? started.run
      : await playUntilEnd(runtime.gameApi, runId, started.runToken, ending === 'sacked');
  return { runtime, run };
}

/** Records every GET of a run; returning nothing lets the original handler answer. */
function spyOnRunFetches(): string[] {
  const fetches: string[] = [];
  mockServer.use(
    http.get('*/api/runs/:runId', ({ request }) => {
      fetches.push(request.url);
    }),
  );
  return fetches;
}

function renderRunFinal(runtime: TestRuntime, runId: string, onPlayAgain = vi.fn()) {
  const rendered = renderWithRuntime(<RunFinal runId={runId} onPlayAgain={onPlayAgain} />, {
    runtime,
  });
  return { ...rendered, onPlayAgain };
}

describe('RunFinal', () => {
  it('shows a loading status while the run loads', () => {
    const runtime = createTestRuntime();
    runtime.runTokenStore.save(UNKNOWN_RUN_ID, 'a-token');

    renderRunFinal(runtime, UNKNOWN_RUN_ID);

    expect(screen.getByRole('status')).toHaveTextContent('Cargando la partida…');
  });

  it('shows the result of a run that just ended from the cache, without fetching it again', async () => {
    const { runtime, run } = await seedRun('finished');
    runtime.queryClient.setQueryData(runQueryKey(run.runId), run);
    const fetches = spyOnRunFetches();

    renderRunFinal(runtime, run.runId);

    expect(screen.getByRole('heading', { level: 1, name: 'Final de la partida' })).toBeVisible();
    expect(screen.getByText('Temporada terminada')).toBeVisible();
    expect(fetches).toEqual([]);
  });

  it('loads the result after a reload with the token this device keeps', async () => {
    const { runtime, run } = await seedRun('finished');

    renderRunFinal(runtime, run.runId);

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Final de la partida' }),
    ).toBeVisible();
    expect(screen.getByText('Temporada terminada')).toBeVisible();
  });

  it('shows a sacked run as a dismissal', async () => {
    const { runtime, run } = await seedRun('sacked');

    renderRunFinal(runtime, run.runId);

    expect(await screen.findByText(/^Destituido en el bloque/)).toBeVisible();
    expect(screen.getByText(/^La directiva te destituyó/)).toBeVisible();
  });

  it('plays again through onPlayAgain', async () => {
    const { runtime, run } = await seedRun('finished');
    const { onPlayAgain } = renderRunFinal(runtime, run.runId);

    fireEvent.click(await screen.findByRole('button', { name: 'Jugar otra partida' }));

    expect(onPlayAgain).toHaveBeenCalledTimes(1);
  });

  it('says the run is not available on this device when there is no token for it', () => {
    renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(screen.getByText(UNAVAILABLE)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/');
  });

  it('gives the link back home a touch-sized target', () => {
    renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveClass(
      'inline-flex',
      'min-h-touch',
      'items-center',
    );
  });

  it('forgets the token and says the run is not available when the API rejects it (403)', async () => {
    const { runtime, run } = await seedRun('finished');
    runtime.runTokenStore.save(run.runId, 'a-token-from-another-run');

    renderRunFinal(runtime, run.runId);

    expect(await screen.findByText(UNAVAILABLE)).toBeVisible();
    expect(runtime.runTokenStore.read(run.runId)).toBeNull();
  });

  it('lets the player retry when the run cannot be loaded', async () => {
    const { runtime, run } = await seedRun('finished');
    mockServer.use(
      http.get('*/api/runs/:runId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );
    renderRunFinal(runtime, run.runId);

    fireEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Final de la partida' }),
    ).toBeVisible();
  });

  it('sends a run still in play back to its page instead of showing a result', async () => {
    const { runtime, run } = await seedRun(null);

    renderRunFinal(runtime, run.runId);

    expect(
      await screen.findByRole('heading', { level: 1, name: 'La partida sigue en juego' }),
    ).toBeVisible();
    expect(screen.getByRole('link', { name: 'Volver a la partida' })).toHaveAttribute(
      'href',
      `/partida/${run.runId}`,
    );
    expect(screen.queryByText('Final de la partida')).not.toBeInTheDocument();
  });

  it('has no accessibility violations for an ended run', async () => {
    const { runtime, run } = await seedRun('sacked');
    const { container } = renderRunFinal(runtime, run.runId);
    await screen.findByRole('heading', { level: 1, name: 'Final de la partida' });

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations when the run is not available', async () => {
    const { container } = renderRunFinal(createTestRuntime(), UNKNOWN_RUN_ID);

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations for a run still in play', async () => {
    const { runtime, run } = await seedRun(null);
    const { container } = renderRunFinal(runtime, run.runId);
    await screen.findByRole('heading', { level: 1, name: 'La partida sigue en juego' });

    expect(await axe(container)).toHaveNoViolations();
  });
});
