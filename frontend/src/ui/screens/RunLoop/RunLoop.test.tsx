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

function optionButton(title: string, optionLabel: string): HTMLElement {
  return within(dilemmaCard(title)).getByRole('button', { name: new RegExp(optionLabel) });
}

/** Chooses an option of a dilemma; nothing is sent until the block is simulated. */
function choose(title: string, optionLabel: string) {
  fireEvent.click(optionButton(title, optionLabel));
}

async function chooseFirstBlock(boardOption = 'Back the board in public') {
  await screen.findByRole('heading', { name: 'Board meeting' });
  choose('Board meeting', boardOption);
  choose('Summer striker', 'Sign the veteran striker');
}

function simulate() {
  fireEvent.click(screen.getByRole('button', SIMULATE));
}

interface SentCommand {
  step: string;
  idempotencyKey: string | null;
}

/** Records every run command in order; returning nothing lets the original handler answer. */
function spyOnCommands(): SentCommand[] {
  const sent: SentCommand[] = [];
  mockServer.use(
    http.post('*/api/runs/:runId/decisions', async ({ request }) => {
      const body = (await request.clone().json()) as { dilemmaId: string };
      sent.push({
        step: `decision:${body.dilemmaId}`,
        idempotencyKey: request.headers.get('Idempotency-Key'),
      });
    }),
    http.post('*/api/runs/:runId/advance', ({ request }) => {
      sent.push({ step: 'advance', idempotencyKey: request.headers.get('Idempotency-Key') });
    }),
  );
  return sent;
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
  it('shows the dilemmas of the block and keeps Simular bloque disabled until each has a choice', async () => {
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });
    const simulateButton = screen.getByRole('button', SIMULATE);
    expect(simulateButton).toBeDisabled();
    expect(screen.getByText('Te quedan 2 dilemas por decidir.')).toBeInTheDocument();

    choose('Board meeting', 'Back the board in public');

    expect(simulateButton).toBeDisabled();
    expect(screen.getByText('Te queda 1 dilema por decidir.')).toBeInTheDocument();

    choose('Summer striker', 'Sign the veteran striker');

    expect(simulateButton).toBeEnabled();
    expect(screen.getByText('Todo decidido: simula el bloque.')).toBeInTheDocument();
  });

  it('shows the block progress of the run', async () => {
    renderRunLoop(await startRun());

    expect(
      await screen.findByRole('progressbar', { name: 'Progreso de la temporada' }),
    ).toHaveAttribute('aria-valuetext', '0 de 5 bloques jugados');
    expect(screen.getByText('Bloque 1 de 5')).toBeInTheDocument();
  });

  it('lets the player change a choice before simulating, without sending anything', async () => {
    const sent = spyOnCommands();
    renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });

    choose('Board meeting', 'Back the board in public');
    choose('Board meeting', 'Publicly confront the board');

    expect(optionButton('Board meeting', 'Back the board in public')).toHaveAttribute(
      'aria-pressed',
      'false',
    );
    expect(optionButton('Board meeting', 'Publicly confront the board')).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(sent).toEqual([]);
  });

  it('numbers each dilemma by its place in the block, also after a reload', async () => {
    const seeded = await startRun();
    await decideInAnotherTab(seeded, 'board-meeting', 'support-the-board', 0);

    renderRunLoop(seeded);

    const card = await screen.findByRole('region', { name: 'Summer striker' });
    expect(within(card).getByText('Dilema 2 de 2')).toBeInTheDocument();
  });

  it('sends each chosen decision once, in order, and then simulates the block', async () => {
    const sent = spyOnCommands();
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

    await screen.findByRole('region', { name: 'Resumen del bloque' });
    expect(sent.map((command) => command.step)).toEqual([
      'decision:board-meeting',
      'decision:summer-striker',
      'advance',
    ]);
  });

  it('simulates the block and shows its results and the standings', async () => {
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

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
    await chooseFirstBlock();

    simulate();

    const heading = await screen.findByRole('heading', { name: 'Resumen del bloque' });
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(screen.getByRole('button', SIMULATE)).toBeDisabled();
  });

  it('runs a double tap on Simular bloque as a single series', async () => {
    const sent = spyOnCommands();
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();
    simulate();

    await screen.findByRole('region', { name: 'Resumen del bloque' });
    expect(sent).toHaveLength(3);
  });

  it('resumes a series cut by the network with the Idempotency-Key of the failed step', async () => {
    let decisions = 0;
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => {
        decisions += 1;
        if (decisions === 2) return HttpResponse.error();
      }),
    );
    const sent = spyOnCommands();
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudo enviar la decisión. Comprueba la conexión y vuelve a intentarlo.',
    );
    expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    simulate();

    await screen.findByRole('region', { name: 'Resumen del bloque' });
    expect(sent.map((command) => command.step)).toEqual([
      'decision:board-meeting',
      'decision:summer-striker',
      'decision:summer-striker',
      'advance',
    ]);
    expect(sent[2]?.idempotencyKey).toBe(sent[1]?.idempotencyKey);
  });

  it('moves the focus to the message when a failure cuts the series', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => HttpResponse.error(), { once: true }),
    );
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

    const alert = await screen.findByRole('alert');
    await waitFor(() => {
      expect(alert).toHaveFocus();
    });
  });

  it('reloads the run and keeps the remaining choices when a 409 cuts the series', async () => {
    let decisions = 0;
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => {
        decisions += 1;
        if (decisions === 2) return problem(409, 'version_conflict');
      }),
    );
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La partida ya había cambiado. Hemos recargado su estado.',
    );
    await waitFor(() => {
      expect(screen.getByRole('button', SIMULATE)).toBeEnabled();
    });
    expect(screen.queryByRole('region', { name: 'Board meeting' })).not.toBeInTheDocument();
    expect(optionButton('Summer striker', 'Sign the veteran striker')).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('keeps Simular bloque disabled while the run reloads after a 409', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await chooseFirstBlock();
    await decideInAnotherTab(seeded, 'board-meeting', 'support-the-board', 0);
    const releaseReload = holdRunReloads();

    simulate();

    await screen.findByRole('alert');
    const simulateButton = screen.getByRole('button', SIMULATE);
    expect(simulateButton).toBeDisabled();
    releaseReload();
    await waitFor(() => {
      expect(simulateButton).toBeEnabled();
    });
  });

  it('shows a message and reloads the run when the simulation itself answers 409', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/advance', () => problem(409, 'version_conflict'), {
        once: true,
      }),
    );
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La partida ya había cambiado. Hemos recargado su estado.',
    );
    await waitFor(() => {
      expect(screen.getByRole('button', SIMULATE)).toBeEnabled();
    });
  });

  it('shows its own message and reloads the run when the API rejects a decision (422)', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => problem(422, 'invalid_option'), {
        once: true,
      }),
    );
    renderRunLoop(await startRun());
    await chooseFirstBlock();

    simulate();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Esa opción ya no es válida. Hemos recargado la partida.',
    );
  });

  it('says the run is not available when the API rejects the token of a command (403)', async () => {
    const seeded = await startRun();
    renderRunLoop(seeded);
    await chooseFirstBlock();
    seeded.runtime.runTokenStore.save(seeded.runId, 'a-token-from-another-run');

    simulate();

    expect(
      await screen.findByText('Esta partida no está disponible en este dispositivo.'),
    ).toBeInTheDocument();
    expect(seeded.runtime.runTokenStore.read(seeded.runId)).toBeNull();
  });

  it('ends the run when the board sacks the manager', async () => {
    const seeded = await startRun();
    const { onRunEnded } = renderRunLoop(seeded);
    await chooseFirstBlock('Publicly confront the board');

    simulate();

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
    choose('Final rotation', 'Rotate the squad');

    simulate();

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
    expect(screen.getByText('Temporada terminada')).toBeInTheDocument();
  });

  it('ends the run when the series finds it already finished', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 4);
    const { onRunEnded } = renderRunLoop(seeded);
    await screen.findByRole('heading', { name: 'Final rotation' });
    choose('Final rotation', 'Rotate the squad');
    // Another tab plays the last block; this one then hears run_already_finished.
    const lastBlock = await decideInAnotherTab(seeded, 'final-rotation', 'rotate-the-squad');
    await seeded.runtime.gameApi.advanceBlock({
      runId: seeded.runId,
      runToken: seeded.runToken,
      idempotencyKey: 'another-tab-advance',
      expectedVersion: lastBlock.version,
    });
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => problem(409, 'run_already_finished'), {
        once: true,
      }),
    );

    simulate();

    await waitFor(() => {
      expect(onRunEnded).toHaveBeenCalledWith(seeded.runId);
    });
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

  it("shows the crest and name of the player's club once a block has been played", async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 1);

    renderRunLoop(seeded);

    const banner = await screen.findByRole('banner', { name: 'Tu equipo' });
    expect(within(banner).getByText('Test FC')).toBeInTheDocument();
    expect(banner.querySelector('svg')).not.toBeNull();
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

  it('has no accessibility violations while the player chooses', async () => {
    const { container } = renderRunLoop(await startRun());
    await screen.findByRole('heading', { name: 'Board meeting' });
    choose('Board meeting', 'Back the board in public');

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations with a block summary on screen', async () => {
    const seeded = await startRun();
    await playBlocks(seeded.runtime.gameApi, seeded.runId, seeded.runToken, 2);
    const { container } = renderRunLoop(seeded);
    await screen.findByRole('region', { name: 'Resumen del bloque' });

    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no accessibility violations with a failure message on screen', async () => {
    mockServer.use(
      http.post('*/api/runs/:runId/decisions', () => HttpResponse.error(), { once: true }),
    );
    const { container } = renderRunLoop(await startRun());
    await chooseFirstBlock();
    simulate();
    await screen.findByRole('alert');

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
