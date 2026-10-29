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
  for (const group of await page.getByRole('group', { name: /^Opciones/ }).all()) {
    await group.getByRole('button').first().click();
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
    await simulate.click();

    if (played === 0) {
      await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeVisible();
      // The run lives on the server and its token in the browser: a reload resumes it.
      await page.reload();
      await expect(page).toHaveURL(runUrl);
      await expect(progress).toHaveAttribute('aria-valuenow', '1');
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
