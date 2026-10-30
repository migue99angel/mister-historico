import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { HttpResponse, http } from 'msw';
import { expect, it, vi } from 'vitest';
import { keyStarterRun } from '../../../../test/keyStarter';
import {
  createTestRuntime,
  mockFixtures,
  mockServer,
  renderWithRuntime,
} from '../../../../test/renderWithRuntime';
import type { RunViewDto } from '../../../application/ports';
import { runQueryKey } from '../../../application/useRun';
import { RunLoop } from './RunLoop';

function setup({ selected = false, loseReply = false } = {}) {
  const runtime = createTestRuntime();
  let run: RunViewDto = keyStarterRun();
  const offer = required(run.keyStarter);
  if (selected) offer.selectedPlayerId = required(offer.candidates[0]).id;
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
  expect(within(panel).getByText('3 sept 2000')).toHaveAttribute('dateTime', '2000-09-03');
  expect(panel).not.toHaveTextContent('2000-09-03');
  expect(within(panel).getByText(/Once previsto/)).toBeVisible();
  expect(within(panel).getAllByText(/Media 90/)).toHaveLength(11);
  const radio = required(within(panel).getAllByRole('radio')[0]);
  expect(within(panel).getAllByText(/Físico 90/).length).toBeGreaterThan(0);
  radio.focus();
  await user.keyboard(' ');
  const confirm = screen.getByRole('button', { name: 'Confirmar titular' });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  await screen.findByText(`Titular confirmado: ${required(view.offer.candidates[0]).displayName}`);
  expect(view.sent).toHaveLength(1);
  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Titular para el partido clave' })).toHaveFocus();
  });
  view.unmount();
  view.runtime.queryClient.clear();
  view.render();
  expect(
    await screen.findByText(
      `Titular confirmado: ${required(view.offer.candidates[0]).displayName}`,
    ),
  ).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Confirmar titular' })).not.toBeInTheDocument();
});

it('locks other commands while confirmation is uncertain and lets the same choice retry', async () => {
  const view = setup({ loseReply: true });
  fireEvent.click(required(screen.getAllByRole('radio')[0]));
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar titular' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/titular/);
  expect(screen.getByRole('button', { name: /Simular/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar titular' }));
  expect(
    await screen.findByText(
      `Titular confirmado: ${required(view.offer.candidates[0]).displayName}`,
    ),
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
    const chosen = required(required(run.keyStarter).candidates[0]);
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
      results: absenceReason === 'fixture_not_played' ? [] : [{ ...required(mockFixtures.resultsForBlock(0)[0]), fixtureId: 'test-fixture' }],
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
    expect(within(outcome).getByText('3 sept 2000')).toHaveAttribute('dateTime', '2000-09-03');
    expect(outcome).not.toHaveTextContent('test-fixture');
    if (absenceReason === 'fixture_not_played') expect(outcome).toHaveTextContent('Partido señalado');
    else {
      const match = required(mockFixtures.resultsForBlock(0)[0]);
      expect(outcome).toHaveTextContent(match.competitionName);
      expect(outcome).toHaveTextContent(match.home.isUser ? match.away.name : match.home.name);
    }
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

function required<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) throw new Error('Expected test fixture value');
  return value;
}

it('recovers another tab selection after a version conflict and announces the error with focus', async () => {
  const view = setup();
  mockServer.use(
    http.post('*/api/runs/:runId/key-starter', () => {
      view.run.version = 1;
      view.offer.selectedPlayerId = required(view.offer.candidates[1]).id;
      return HttpResponse.json(
        { type: 'about:blank', title: 'Conflict', status: 409, code: 'version_conflict' },
        { status: 409, headers: { 'Content-Type': 'application/problem+json' } },
      );
    }),
  );
  fireEvent.click(required(screen.getAllByRole('radio')[0]));
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar titular' }));
  expect(
    await screen.findByText(
      `Titular confirmado: ${required(view.offer.candidates[1]).displayName}`,
    ),
  ).toBeVisible();
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('Hemos recargado');
  expect(alert).toHaveFocus();
  expect(screen.queryByRole('button', { name: 'Reintentar titular' })).not.toBeInTheDocument();
});

it('does not offer a selection when the server has no offer', () => {
  const runtime = createTestRuntime();
  const run = keyStarterRun();
  run.keyStarter = null;
  runtime.runTokenStore.save(run.runId, 'test-token');
  runtime.queryClient.setQueryData(runQueryKey(run.runId), run);
  renderWithRuntime(<RunLoop runId={run.runId} onRunEnded={vi.fn()} />, { runtime });
  expect(
    screen.queryByRole('region', { name: 'Titular para el partido clave' }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Simular bloque' })).toBeVisible();
});

it('blocks selecting a starter while an advance has an uncertain outcome', async () => {
  setup();
  mockServer.use(http.post('*/api/runs/:runId/advance', () => HttpResponse.error()));
  fireEvent.click(screen.getByRole('button', { name: 'Simular bloque sin elegir titular' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo simular');
  expect(screen.getAllByRole('radio')[0]).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Simular bloque sin elegir titular' })).toBeEnabled();
});

it('exposes the captured comparison with labelled keyboard controls and no accessibility violations', async () => {
  setup();
  const panel = screen.getByRole('region', { name: 'Titular para el partido clave' });
  expect(await axe(panel)).toHaveNoViolations();
});
