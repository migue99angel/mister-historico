import { fireEvent, screen, waitFor, within } from '@testing-library/react';
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
import type { GameApi } from '../../../application/ports';
import { RunLoop } from './RunLoop';

const UNKNOWN_RUN_ID = '00000000-0000-4000-8000-000000000000';
const SIMULATE = { name: /Simular bloque/ };

interface SeededRun {
  runtime: TestRuntime;
  runId: string;
  runToken: string;
}

async function startRun(): Promise<SeededRun> {
  const runtime = createTestRuntime();
  const started = await runtime.gameApi.startRun({ seasonId: mockFixtures.TEST_SEASON_ID });
  runtime.runTokenStore.save(started.run.runId, started.runToken);
  return { runtime, runId: started.run.runId, runToken: started.runToken };
}

/** Plays whole blocks through the API, always taking each dilemma's first option. */
async function playBlocks(gameApi: GameApi, runId: string, runToken: string, blocks: number) {
  let run = await gameApi.getRun(runId, runToken);
  for (let played = 0; played < blocks; played += 1) {
    for (const dilemma of run.pendingDilemmas) {
      const optionId = dilemma.options[0]?.id ?? '';
      run = await gameApi.takeDecision({
        runId,
        runToken,
        idempotencyKey: `seed-${dilemma.id}`,
        dilemmaId: dilemma.id,
        optionId,
        expectedVersion: run.version,
      });
    }
    run = await gameApi.advanceBlock({
      runId,
      runToken,
      idempotencyKey: `seed-advance-${String(played)}`,
      expectedVersion: run.version,
    });
  }
  return run;
}

function renderRunLoop({ runtime, runId }: SeededRun, onRunEnded = vi.fn()) {
  const rendered = renderWithRuntime(<RunLoop runId={runId} onRunEnded={onRunEnded} />, {
    runtime,
  });
  return { ...rendered, onRunEnded };
}

function dilemmaCard(title: string): HTMLElement {
  return screen.getByRole('region', { name: title });
}

/** Chooses an option of a dilemma and confirms it. */
function decide(title: string, optionLabel: string) {
  const card = dilemmaCard(title);
  fireEvent.click(within(card).getByRole('button', { name: new RegExp(optionLabel) }));
  fireEvent.click(screen.getByRole('button', { name: `Confirmar decisión: ${title}` }));
}

async function decideAndWait(title: string, optionLabel: string) {
  decide(title, optionLabel);
  await waitFor(() => {
    expect(screen.queryByRole('region', { name: title })).not.toBeInTheDocument();
  });
}

/** Records the Idempotency-Key of every request to a run command; the original handler answers. */
function spyOnCommand(command: 'decisions' | 'advance'): (string | null)[] {
  const keys: (string | null)[] = [];
  mockServer.use(
    http.post(`*/api/runs/:runId/${command}`, ({ request }) => {
      keys.push(request.headers.get('Idempotency-Key'));
    }),
  );
  return keys;
}

/** Decides through the API, as another tab or device of the same player would. */
async function decideInAnotherTab(
  { runtime, runId, runToken }: SeededRun,
  dilemmaId: string,
  optionId: string,
  expectedVersion?: number,
) {
  const version = expectedVersion ?? (await runtime.gameApi.getRun(runId, runToken)).version;
  return runtime.gameApi.takeDecision({
    runId,
    runToken,
    idempotencyKey: `another-tab-${dilemmaId}`,
    dilemmaId,
    optionId,
    expectedVersion: version,
  });
}

/** Holds every GET of the run until released; the original handler then answers it. */
function holdRunReloads(): () => void {
  let release: () => void = () => undefined;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  mockServer.use(
    http.get('*/api/runs/:runId', async () => {
      await held;
    }),
  );
  return () => {
    release();
  };
}

function problem(status: number, code: string) {
  return HttpResponse.json(
    { type: 'about:blank', title: code, status, code },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );
}

describe('RunLoop', () => {
  it('shows the dilemmas of the block and keeps Simular bloque disabled while any is pending', async () => {
    renderRunLoop(await startRun());

    expect(await screen.findByRole('heading', { name: 'Board meeting' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Summer striker' })).toBeInTheDocument();
    expect(screen.getByRole('button', SIMULATE)).toBeDisabled();
    expect(screen.getByText('Te quedan 2 dilemas por decidir.')).toBeInTheDocument();
  });

  it('shows the block progress of the run', async () => {
    renderRunLoop(await startRun());

    expect(
      await screen.findByRole('progressbar', { name: 'Progreso de la temporada' }),
    ).toHaveAttribute('aria-valuetext', '0 de 5 bloques jugados');
    expect(screen.getByText('Bloque 1 de 5')).toBeInTheDocument();
  });

  it('marks the chosen option and only then lets the player confirm it', async () => {
    renderRunLoop(await startRun());
    const card = await screen.findByRole('region', { name: 'Board meeting' });
    const confirm = screen.getByRole('button', { name: 'Confirmar decisión: Board meeting' });
    expect(confirm).toBeDisabled();

    const option = within(card).getByRole('button', { name: /Back the board in public/ });
    fireEvent.click(option);

    expect(option).toHaveAttribute('aria-pressed', 'true');
    expect(confirm).toBeEnabled();
  });

  it('takes the decision and updates the view with the remaining dilemmas', async () => {
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    await decideAndWait('Board meeting', 'Back the board in public');

    expect(screen.getByText('Te queda 1 dilema por decidir.')).toBeInTheDocument();
    expect(screen.getByText(/Board meeting: Back the board in public/)).toBeInTheDocument();
  });

  it('enables Simular bloque once every dilemma is decided and moves the focus to it', async () => {
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    await decideAndWait('Board meeting', 'Back the board in public');
    await decideAndWait('Summer striker', 'Sign the veteran striker');

    const simulate = screen.getByRole('button', SIMULATE);
    expect(simulate).toBeEnabled();
    await waitFor(() => {
      expect(simulate).toHaveFocus();
    });
  });

  it('sends a double tap on the confirmation only once', async () => {
    const keys = spyOnCommand('decisions');
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    const card = dilemmaCard('Board meeting');
    fireEvent.click(within(card).getByRole('button', { name: /Back the board in public/ }));
    const confirm = screen.getByRole('button', { name: 'Confirmar decisión: Board meeting' });
    fireEvent.click(confirm);
    fireEvent.click(confirm);

    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    });
    expect(keys).toHaveLength(1);
  });

  it('retries a decision lost to the network with the same Idempotency-Key', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => HttpResponse.error(), { once: true }),
    );
    const keys = spyOnCommand('decisions');
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    decide('Board meeting', 'Back the board in public');
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo enviar la decisión. Comprueba la conexión y vuelve a intentarlo.',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar decisión: Board meeting' }));

    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    });
    expect(keys).toHaveLength(2);
    expect(keys[1]).toBe(keys[0]);
  });

  it('shows a message and reloads the run when the API answers 409', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    // Another tab decides first, so this view is stale.
    await seeded.runtime.gameApi.takeDecision({
      runId: seeded.runId,
      runToken: seeded.runToken,
      idempotencyKey: 'another-tab-attempt',
      dilemmaId: 'board-meeting',
      optionId: 'support-the-board',
      expectedVersion: 0,
    });

    decide('Summer striker', 'Sign the veteran striker');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La partida ya había cambiado. Hemos recargado su estado.',
    );
    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    });
    expect(screen.getByRole('region', { name: 'Summer striker' })).toBeInTheDocument();
  });

  it('keeps the commands disabled while the run reloads after a 409', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideInAnotherTab(seeded, 'board-meeting', 'support-the-board', 0);
    const releaseReload = holdRunReloads();

    decide('Summer striker', 'Sign the veteran striker');

    await screen.findByRole('alert');
    const confirm = screen.getByRole('button', { name: 'Confirmar decisión: Summer striker' });
    expect(confirm).toBeDisabled();
    releaseReload();
    await waitFor(() => {
      expect(confirm).toBeEnabled();
    });
  });

  it('moves the focus to the dilemmas when a 409 reload removes the dilemma being decided', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideInAnotherTab(seeded, 'board-meeting', 'support-the-board', 0);

    decide('Board meeting', 'Back the board in public');

    await waitFor(() => {
      expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Decisiones del bloque' })).toHaveFocus();
    });
  });

  it('shows its own message and reloads the run when the API rejects a decision (422)', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => problem(422, 'invalid_option'), {
        once: true,
      }),
    );
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    decide('Board meeting', 'Back the board in public');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Esa opción ya no es válida. Hemos recargado la partida.',
    );
  });

  it('shows a message and reloads the run when Simular bloque answers 409', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideAndWait('Board meeting', 'Back the board in public');
    await decideAndWait('Summer striker', 'Sign the veteran striker');
    // Another tab simulates the block first.
    await seeded.runtime.gameApi.advanceBlock({
      runId: seeded.runId,
      runToken: seeded.runToken,
      idempotencyKey: 'another-tab-advance',
      expectedVersion: 2,
    });

    fireEvent.click(screen.getByRole('button', SIMULATE));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La partida ya había cambiado. Hemos recargado su estado.',
    );
    expect(await screen.findByRole('heading', { name: 'Captain complaint' })).toBeInTheDocument();
  });

  it('ends the run when Simular bloque finds it already finished', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 4);
    const lastBlock = await decideInAnotherTab(seeded, 'final-rotation', 'rotate-the-squad');
    const { onRunEnded } = renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Decisiones del bloque' });
    // Another tab simulates the last block; this one then hears run_already_finished.
    await seeded.runtime.gameApi.advanceBlock({
      runId: seeded.runId,
      runToken: seeded.runToken,
      idempotencyKey: 'another-tab-advance',
      expectedVersion: lastBlock.version,
    });
    mockServer.use(
      http.post('*/api/runs/:runId/advance', () => problem(409, 'run_already_finished'), {
        once: true,
      }),
    );

    fireEvent.click(screen.getByRole('button', SIMULATE));

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
  });

  it('says the run is not available when the API rejects the token of a command (403)', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    seeded.runtime.runTokenStore.save(seeded.runId, 'a-token-from-another-run');

    decide('Board meeting', 'Back the board in public');

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
    expect(seeded.runtime.runTokenStore.read(seeded.runId)).toBeNull();
  });

  it("shows the crest and name of the player's club once a block has been played", async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 1);

    renderRunLoop(seeded);

    const banner = await screen.findByRole('banner', { name: 'Tu equipo' });
    expect(within(banner).getByText('Test FC')).toBeInTheDocument();
    expect(banner.querySelector('svg')).not.toBeNull();
  });

  it('simulates the block and shows its results and the standings', async () => {
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideAndWait('Board meeting', 'Back the board in public');
    await decideAndWait('Summer striker', 'Sign the veteran striker');

    fireEvent.click(screen.getByRole('button', SIMULATE));

    const summary = await screen.findByRole('region', { name: 'Resumen del bloque' });
    expect(within(summary).getByText('August · 1 victoria y 1 empate')).toBeInTheDocument();
    expect(within(summary).getAllByText('Rovers Prueba')).not.toHaveLength(0);
    expect(within(summary).getByText('Derby')).toBeInTheDocument();
    const standings = screen.getByRole('table', { name: 'Liga Test' });
    expect(within(standings).getByRole('row', { current: true })).toHaveTextContent('Test FC');
    expect(screen.getByText('Bloque 2 de 5')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Captain complaint' })).toBeInTheDocument();
  });

  it('moves the focus to the block summary once the simulation disables the button', async () => {
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideAndWait('Board meeting', 'Back the board in public');
    await decideAndWait('Summer striker', 'Sign the veteran striker');

    fireEvent.click(screen.getByRole('button', SIMULATE));

    const heading = await screen.findByRole('heading', { name: 'Resumen del bloque' });
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(screen.getByRole('button', SIMULATE)).toBeDisabled();
  });

  it('simulates a double tap on Simular bloque only once', async () => {
    const keys = spyOnCommand('advance');
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideAndWait('Board meeting', 'Back the board in public');
    await decideAndWait('Summer striker', 'Sign the veteran striker');

    const simulate = screen.getByRole('button', SIMULATE);
    fireEvent.click(simulate);
    fireEvent.click(simulate);

    await screen.findByRole('region', { name: 'Resumen del bloque' });
    expect(keys).toHaveLength(1);
  });

  it('ends the run when the board sacks the manager', async () => {
    const seeded = await startRun();
    const { onRunEnded } = renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Board meeting' });
    await decideAndWait('Board meeting', 'Publicly confront the board');
    await decideAndWait('Summer striker', 'Sign the veteran striker');

    fireEvent.click(screen.getByRole('button', SIMULATE));

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
    expect(onRunEnded).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Destituido en el bloque 1 de 5')).toBeInTheDocument();
  });

  it('ends the run when the last block of the season is simulated', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 4);
    const { onRunEnded } = renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Final rotation' });
    await decideAndWait('Final rotation', 'Rotate the squad');

    fireEvent.click(screen.getByRole('button', SIMULATE));

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
    expect(screen.getByText('Temporada terminada')).toBeInTheDocument();
  });

  it('ends at once a run that had already ended when it loads', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 5);

    const { onRunEnded } = renderRunLoop(seeded);

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
    expect(screen.queryByRole('button', SIMULATE)).not.toBeInTheDocument();
  });

  it('says the run is not available on this device when there is no token for it', () => {
    renderRunLoop({ runtime: createTestRuntime(), runId: UNKNOWN_RUN_ID, runToken: '' });

    expect(
      screen.getByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveAttribute('href', '/');
  });

  it('gives the link back home a touch-sized target', () => {
    renderRunLoop({ runtime: createTestRuntime(), runId: UNKNOWN_RUN_ID, runToken: '' });

    expect(screen.getByRole('link', { name: 'Volver al inicio' })).toHaveClass(
      'inline-flex',
      'min-h-touch',
      'items-center',
    );
  });

  it('forgets the token and says the run is not available when the API rejects it (403)', async () => {
    const seeded = await startRun();
    seeded.runtime.runTokenStore.save(seeded.runId, 'a-token-from-another-run');

    renderRunLoop(seeded);

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
    expect(seeded.runtime.runTokenStore.read(seeded.runId)).toBeNull();
  });

  it('forgets the token and says the run is not available when the API does not know it (404)', async () => {
    const runtime = createTestRuntime();
    runtime.runTokenStore.save(UNKNOWN_RUN_ID, 'a-token');

    renderRunLoop({ runtime, runId: UNKNOWN_RUN_ID, runToken: 'a-token' });

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
    expect(runtime.runTokenStore.read(UNKNOWN_RUN_ID)).toBeNull();
  });

  it('lets the player retry when the run cannot be loaded', async () => {
    mockServer.use(
      http.get('*/api/runs/:runId', () => HttpResponse.text('down', { status: 500 }), {
        once: true,
      }),
    );
    renderRunLoop(await startRun());

    fireEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('heading', { name: 'Board meeting' })).toBeInTheDocument();
  });

  it('has no accessibility violations while the player decides', async () => {
    const { container } = renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations with a block summary on screen', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 2);
    const { container } = renderRunLoop(seeded);
    await screen.findByRole('region', { name: 'Resumen del bloque' });

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations when the run is not available', async () => {
    const { container } = renderRunLoop({
      runtime: createTestRuntime(),
      runId: UNKNOWN_RUN_ID,
      runToken: '',
    });

    expect(await axe(container)).toHaveNoViolations();
  });
});
