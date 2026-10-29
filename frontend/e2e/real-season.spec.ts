import { readFileSync } from 'node:fs';

import { expect, test, type Page, type Response } from '@playwright/test';

import { expectNoHorizontalScroll } from './support/a11y';

// Served by the real API of playwright.config.ts (e2e/support/real_api.py): production
// composition, PostgreSQL, the engine and the golden seed. No MSW in this file.
const GOLDEN_PATH = new URL(
  '../../backend/tests/golden/test_fc_2000_01.golden.json',
  import.meta.url,
);

interface RunViewJson {
  status: string;
  lastBlockSummary: unknown;
}

/** The view the golden client got from each block advance: the one with a new summary. */
function goldenAdvanceViews(): RunViewJson[] {
  const views = JSON.parse(readFileSync(GOLDEN_PATH, 'utf-8')) as RunViewJson[];
  return views.filter(
    (view, index) =>
      index > 0 &&
      JSON.stringify(view.lastBlockSummary) !== JSON.stringify(views[index - 1]?.lastBlockSummary),
  );
}

function blockOutcome({ status, lastBlockSummary }: RunViewJson): RunViewJson {
  return { status, lastBlockSummary };
}

function isAdvance(response: Response): boolean {
  return (
    response.request().method() === 'POST' && /\/api\/runs\/[^/]+\/advance$/.test(response.url())
  );
}

/** Picks the first option of every dilemma, the decision policy of the backend golden. */
async function decideFirstOptions(page: Page): Promise<void> {
  while (await page.getByRole('group', { name: /^Opciones/ }).count()) {
    const group = page.getByRole('group', { name: /^Opciones/ }).first();
    const name = await group.getAttribute('aria-label');
    await group.getByRole('button').first().click();
    await page
      .getByRole('button', { name: /^Confirmar:/ })
      .first()
      .click();
    await expect(page.getByRole('group', { name: name ?? '', exact: true })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
  }
}

test('Test FC is played to the end against the real API, surviving reloads, with no sideways scroll', async ({
  page,
}) => {
  // Read each body as it arrives: a reload discards the bodies of earlier responses.
  const advances: Promise<RunViewJson>[] = [];
  page.on('response', (response) => {
    if (isAdvance(response)) advances.push(response.json() as Promise<RunViewJson>);
  });

  await page.goto('/');
  await page.getByRole('button', { name: /^Elegir Test FC/ }).click();
  await expect(page).toHaveURL(/\/equipo\//);
  await expectNoHorizontalScroll(page);

  await page.getByRole('button', { name: 'Empezar' }).click();
  await expect(page).toHaveURL(/\/partida\/[0-9a-f-]+$/);
  const runUrl = page.url();
  const progress = page.getByRole('progressbar', { name: 'Progreso de la temporada' });
  const simulate = page.getByRole('button', { name: 'Simular bloque' });
  await expect(simulate).toBeVisible();
  const totalBlocks = Number(await progress.getAttribute('aria-valuemax'));
  expect(totalBlocks).toBeGreaterThan(1);

  for (let played = 0; played < totalBlocks; played += 1) {
    await expect(progress).toHaveAttribute('aria-valuenow', String(played));
    await expectNoHorizontalScroll(page);
    await decideFirstOptions(page);
    const advanced = page.waitForResponse(isAdvance);
    if (played === 0) {
      await simulate.evaluate((button) => {
        (button as { click: () => void }).click();
        (button as { click: () => void }).click();
      });
    } else {
      await simulate.click();
    }
    expect((await advanced).status()).toBe(200);
    const skip = page.getByRole('button', { name: 'Mostrar todos' });
    await expect(skip).toBeVisible();
    await expect(page.getByRole('table')).toHaveCount(0);
    await expect(page.getByRole('region', { name: 'Estado del equipo' })).toHaveCount(0);
    if (played === 1 || played === totalBlocks - 1) {
      await expect(page).toHaveURL(runUrl);
      await skip.click();
    }

    if (played === 0) {
      await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeVisible();
      // The run lives on the server and its token in the browser: a reload resumes it.
      await page.reload();
      await expect(page).toHaveURL(runUrl);
      await expect(progress).toHaveAttribute('aria-valuenow', '1');
      await expect(skip).toHaveCount(0);
      await expect(page.getByRole('table')).not.toHaveCount(0);
      await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeVisible();
    }
  }

  await expect(page).toHaveURL(`${runUrl}/final`);
  const finalTitle = page.getByRole('heading', { level: 1, name: 'Final de la partida' });
  await expect(finalTitle).toBeVisible();
  await expect(page.getByText('Has llegado al final de la temporada.')).toBeVisible();
  await expect(progress).toHaveAttribute('aria-valuenow', String(totalBlocks));
  await expectNoHorizontalScroll(page);

  // Block by block, the real engine with the golden seed and policy plays the backend golden.
  const played = await Promise.all(advances);
  expect(played.map(blockOutcome)).toEqual(goldenAdvanceViews().map(blockOutcome));

  await page.reload();
  await expect(page).toHaveURL(`${runUrl}/final`);
  await expect(finalTitle).toBeVisible();
  await expect(page.getByText('Has llegado al final de la temporada.')).toBeVisible();
});

test('the board sacks the Test FC manager in block two and the dismissal survives a reload', async ({
  page,
}) => {
  // Same profile A, seed 2000 and last-option policy as the backend dismissal E2E
  // (backend/tests/golden/season_play.py). The real API launcher already pins this seed.
  const dismissalBlock = 2;
  await page.goto('/');
  await page.getByRole('button', { name: /^Elegir Test FC/ }).click();
  await page.getByRole('button', { name: 'Empezar' }).click();
  await expect(page).toHaveURL(/\/partida\/[0-9a-f-]+$/);
  const runUrl = page.url();
  const progress = page.getByRole('progressbar', { name: 'Progreso de la temporada' });
  const simulate = page.getByRole('button', { name: 'Simular bloque' });

  let dismissed: unknown;
  for (let played = 0; played < dismissalBlock; played += 1) {
    await expect(progress).toHaveAttribute('aria-valuenow', String(played));
    await expectNoHorizontalScroll(page);
    const dilemmas = page.getByRole('group', { name: /^Opciones/ });
    expect(await dilemmas.count()).toBeGreaterThan(0);
    while (await dilemmas.count()) {
      const name = await dilemmas.first().getAttribute('aria-label');
      await dilemmas.first().getByRole('button').last().click();
      await page
        .getByRole('button', { name: /^Confirmar:/ })
        .first()
        .click();
      await expect(page.getByRole('group', { name: name ?? '', exact: true })).toHaveCount(0);
      await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
    }
    const advanced = page.waitForResponse(isAdvance);
    await simulate.click();
    const response = await advanced;
    expect(response.status()).toBe(200);
    expect(response.fromServiceWorker()).toBe(false);
    const view: unknown = await response.json();
    if (played + 1 === dismissalBlock) {
      expect(view).toMatchObject({
        status: 'sacked',
        block: { number: dismissalBlock },
        pendingDilemmas: [],
      });
      dismissed = view;
      await expect(page).toHaveURL(runUrl);
      await page.getByRole('button', { name: 'Mostrar todos' }).click();
    } else {
      expect(view).toMatchObject({ status: 'in_progress' });
    }
  }

  await expect(page).toHaveURL(`${runUrl}/final`);
  const finalTitle = page.getByRole('heading', { level: 1, name: 'Final de la partida' });
  const dismissal = page.getByText(/^La directiva te destituyó/);
  const standings = page.getByRole('region', { name: 'Clasificación en la destitución' });
  await expect(finalTitle).toBeVisible();
  await expect(dismissal).toBeVisible();
  await expect(standings).toBeVisible();
  await expect(progress).toHaveAttribute('aria-valuenow', String(dismissalBlock));
  expect(Number(await progress.getAttribute('aria-valuemax'))).toBeGreaterThan(dismissalBlock);
  await expect(simulate).toHaveCount(0);
  await expectNoHorizontalScroll(page);

  const recovered = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET' && /\/api\/runs\/[^/]+$/.test(response.url()),
  );
  await page.reload();
  const response = await recovered;
  expect(response.status()).toBe(200);
  expect(response.fromServiceWorker()).toBe(false);
  expect(await response.json()).toEqual(dismissed);
  await expect(page).toHaveURL(`${runUrl}/final`);
  await expect(finalTitle).toBeVisible();
  await expect(dismissal).toBeVisible();
  await expect(standings).toBeVisible();
  await expect(progress).toHaveAttribute('aria-valuenow', String(dismissalBlock));
  await expect(simulate).toHaveCount(0);
  await expectNoHorizontalScroll(page);
});

test('a confirmed decision shows real changes and reload preserves state and log without a receipt', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByRole('button', { name: /^Elegir Test FC/ }).click();
  await page.getByRole('button', { name: 'Empezar' }).click();
  const group = page.getByRole('group', { name: /^Opciones/ }).first();
  await group.getByRole('button').first().click();
  await expect(page.getByRole('button', { name: 'Simular bloque' })).toBeDisabled();
  const decided = page.waitForResponse(
    (response) => response.request().method() === 'POST' && response.url().endsWith('/decisions'),
  );
  await page
    .getByRole('button', { name: /^Confirmar:/ })
    .first()
    .click();
  const response = await decided;
  expect(response.fromServiceWorker()).toBe(false);
  const view = (await response.json()) as {
    state: { morale: number; boardConfidence: number; fitness: number };
    decisions: unknown[];
  };
  const feedback = page.getByRole('region', { name: 'Última decisión' });
  await expect(feedback).toBeVisible();
  await expect(feedback.getByText(/^Moral:/)).toContainText(`→ ${String(view.state.morale)}`);
  const panel = page.getByRole('region', { name: 'Estado del equipo' });
  await expect(
    panel.getByText(`Confianza de la directiva: ${String(view.state.boardConfidence)}`, {
      exact: true,
    }),
  ).toBeVisible();
  await expectNoHorizontalScroll(page);
  await page.reload();
  await expect(
    panel.getByText(`Moral: ${String(view.state.morale)}`, { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('region', { name: 'Última decisión' })).toHaveCount(0);
  const log = page.getByRole('region', { name: 'Decisiones confirmadas' });
  await log.getByText('Ver decisiones confirmadas').click();
  await expect(log.getByRole('listitem')).toHaveCount(view.decisions.length);
});
