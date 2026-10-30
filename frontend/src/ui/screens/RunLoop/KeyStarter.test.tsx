import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { expect, it, vi } from 'vitest';
import { keyStarterRun } from '../../../../test/keyStarter';
import {
  createTestRuntime,
  mockServer,
  renderWithRuntime,
} from '../../../../test/renderWithRuntime';
import type { RunViewDto } from '../../../application/ports';
import { runQueryKey } from '../../../application/useRun';
import { RunLoop } from './RunLoop';

function setup({ selected = false, loseReply = false } = {}) {
  const runtime = createTestRuntime();
  let run: RunViewDto = keyStarterRun();
  const offer = run.keyStarter!;
  if (selected) offer.selectedPlayerId = offer.candidates[0]!.id;
  run.pendingDilemmas = [];
  // Current conditions disagree deliberately: the offer must retain its captured values.
  run.squad.players = run.squad.players.map((p) => ({ ...p, fitness: 1, morale: 2 }));
  runtime.runTokenStore.save(run.runId, 'test-token');
  runtime.queryClient.setQueryData(runQueryKey(run.runId), run);
  const sent: unknown[] = [];
  mockServer.use(
    http.get('*/api/runs/:runId', () => HttpResponse.json(run)),
    http.post('*/api/runs/:runId/key-starter', async ({ request }) => {
      const body = (await request.json()) as { playerId: string };
      sent.push(body);
      if (loseReply && sent.length === 1) return HttpResponse.error();
      run = {
        ...run,
        version: run.version + 1,
        keyStarter: { ...offer, selectedPlayerId: body.playerId },
      };
      return HttpResponse.json(run);
    }),
  );
  const render = () =>
    renderWithRuntime(<RunLoop runId={run.runId} onRunEnded={vi.fn()} />, { runtime });
  return { ...render(), render, runtime, run, offer, sent };
}

it('compares the captured forecast and reserves, confirms by keyboard and restores after reload', async () => {
  const user = userEvent.setup();
  const view = setup();
  const panel = screen.getByRole('region', { name: 'Titular para el partido clave' });
  expect(within(panel).getByText(/Test Rovers/)).toBeVisible();
  expect(within(panel).getByText(/2000-09-03/)).toBeVisible();
  expect(within(panel).getByText(/Once previsto/)).toBeVisible();
  expect(within(panel).getAllByText(/Media 90/)).toHaveLength(11);
  const radio = within(panel).getAllByRole('radio')[0]!;
  expect(within(panel).getAllByText(/Físico 90/).length).toBeGreaterThan(0);
  radio.focus();
  await user.keyboard(' ');
  const confirm = screen.getByRole('button', { name: 'Confirmar titular' });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  await screen.findByText(`Titular confirmado: ${view.offer.candidates[0]!.displayName}`);
  expect(view.sent).toHaveLength(1);
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Titular para el partido clave' })).toHaveFocus();
  });
  view.unmount();
  view.runtime.queryClient.clear();
  view.render();
  expect(
    await screen.findByText(`Titular confirmado: ${view.offer.candidates[0]!.displayName}`),
  ).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar titular' })).not.toBeInTheDocument();
});

it('locks other commands while confirmation is uncertain and lets the same choice retry', async () => {
  const view = setup({ loseReply: true });
  fireEvent.click(screen.getAllByRole('radio')[0]!);
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar titular' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/titular/);
  expect(screen.getByRole('button', { name: /Simular/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar titular' }));
  expect(
    await screen.findByText(`Titular confirmado: ${view.offer.candidates[0]!.displayName}`),
  ).toBeVisible();
  expect(view.sent).toHaveLength(2);
});

it('offers explicit simulation without choosing and never sends a selection', () => {
  const view = setup();
  expect(screen.getByRole('button', { name: /Simular bloque sin elegir titular/ })).toBeEnabled();
  expect(view.sent).toHaveLength(0);
});

it.each(['injured', 'not_in_squad', 'youth_conflict', 'fixture_not_played', null] as const)(
  'shows actual participation or absence (%s) after closure',
  (absenceReason) => {
    const runtime = createTestRuntime();
    const run = keyStarterRun();
    const chosen = run.keyStarter!.candidates[0]!;
    const ids =
      absenceReason === 'fixture_not_played'
        ? []
        : absenceReason === null
          ? [chosen.id]
          : ['actual-reserve'];
    run.keyStarter = null;
    run.lastBlockSummary = {
      blockNumber: 1,
      label: 'Bloque Test',
      results: [],
      standings: [],
      events: [],
      injuries: [],
      keyStarterOutcome: {
        fixtureId: 'test-fixture',
        date: '2000-09-03',
        playerId: chosen.id,
        starterIds: ids,
        absenceReason,
      },
    };
    runtime.runTokenStore.save(run.runId, 'test-token');
    runtime.queryClient.setQueryData(runQueryKey(run.runId), run);
    renderWithRuntime(<RunLoop runId={run.runId} onRunEnded={vi.fn()} />, { runtime });
    const outcome = screen.getByRole('region', { name: 'Resultado del titular elegido' });
    expect(outcome).toHaveTextContent(chosen.displayName);
    if (absenceReason === null) expect(outcome).toHaveTextContent('Jugó de titular');
    else
      expect(outcome).toHaveTextContent(
        {
          injured: 'lesión',
          not_in_squad: 'plantilla',
          youth_conflict: 'cantera',
          fixture_not_played: 'no se disputó',
        }[absenceReason],
      );
    if (ids.length) expect(within(outcome).getByText('Once real')).toBeVisible();
  },
);
