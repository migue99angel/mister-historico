import { expect, test, type Page, type Response } from '@playwright/test';
import { expectNoHorizontalScroll, expectNoAxeViolations } from './support/a11y';

interface StarterRun {
  version: number;
  keyStarter?: {
    fixtureId: string;
    selectedPlayerId: string | null;
    candidates: { id: string; displayName: string }[];
  } | null;
  lastBlockSummary: {
    keyStarterOutcome?: {
      playerId: string;
      starterIds: string[];
      absenceReason: string | null;
    } | null;
  } | null;
}
const isSelection = (response: Response) =>
  response.request().method() === 'POST' && response.url().endsWith('/key-starter');
const isAdvance = (response: Response) =>
  response.request().method() === 'POST' && response.url().endsWith('/advance');

async function start(page: Page): Promise<StarterRun> {
  await page.goto('/');
  await page.getByRole('button', { name: /^Elegir Test FC/ }).click();
  const started = page.waitForResponse(
    (r) => r.request().method() === 'POST' && r.url().endsWith('/api/runs'),
  );
  await page.getByRole('button', { name: 'Empezar' }).click();
  const run = ((await (await started).json()) as { run: StarterRun }).run;
  await expect(page.getByRole('button', { name: /^Simular bloque/ })).toBeVisible();
  return run;
}

async function decide(page: Page, sale?: string) {
  while (await page.getByRole('group', { name: /^Opciones/ }).count()) {
    const group = page.getByRole('group', { name: /^Opciones/ }).first();
    const name = await group.getAttribute('aria-label');
    const saleOption = sale ? group.getByRole('button', { name: sale }) : null;
    if (saleOption && (await saleOption.count())) await saleOption.click();
    else await group.getByRole('button').first().click();
    await page
      .getByRole('button', { name: /^Confirmar:/ })
      .first()
      .click();
    await expect(page.getByRole('group', { name: name ?? '', exact: true })).toHaveCount(0);
  }
}

async function advance(page: Page): Promise<StarterRun> {
  const response = page.waitForResponse(isAdvance);
  await page.getByRole('button', { name: /^Simular bloque/ }).click();
  const run = (await (await response).json()) as StarterRun;
  const skip = page.getByRole('button', { name: 'Mostrar todos' });
  await expect(skip).toBeVisible();
  await skip.click();
  await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeVisible();
  return run;
}

test('real starter selection retries a network error, ignores double taps and survives reload before participation is shown', async ({
  page,
}) => {
  const initial = await start(page);
  expect(initial.keyStarter?.candidates.length).toBeGreaterThanOrEqual(2);
  const candidate = required(required(initial.keyStarter).candidates[0]);
  const panel = page.getByRole('region', { name: 'Titular para el partido clave' });
  await expect(panel).toBeVisible();
  await expectNoHorizontalScroll(page);
  await expectNoAxeViolations(page);
  await expect(panel.getByText(/Once previsto/)).toBeVisible();
  await panel.getByRole('radio').first().check();
  await page.route(
    '**/api/runs/*/key-starter',
    async (route) => {
      await route.abort();
    },
    { times: 1 },
  );
  await page.getByRole('button', { name: 'Confirmar titular' }).click();
  await expect(page.getByRole('alert')).toContainText('No se pudo confirmar el titular');
  await expect(page.getByRole('button', { name: /^Simular bloque/ })).toBeDisabled();
  const requests: string[] = [];
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().endsWith('/key-starter'))
      requests.push(request.headers()['idempotency-key'] ?? '');
  });
  const selectedResponse = page.waitForResponse(isSelection);
  await page.getByRole('button', { name: 'Reintentar titular' }).evaluate((button) => {
    (button as { click: () => void }).click();
    (button as { click: () => void }).click();
  });
  expect((await selectedResponse).status()).toBe(200);
  await expect(page.getByText(`Titular confirmado: ${candidate.displayName}`)).toBeVisible();
  expect(requests).toHaveLength(1);
  await expect(page.getByRole('heading', { name: 'Titular para el partido clave' })).toBeFocused();
  await page.reload();
  await expect(page.getByText(`Titular confirmado: ${candidate.displayName}`)).toBeVisible();
  await decide(page);
  const completed = await advance(page);
  expect(completed.lastBlockSummary?.keyStarterOutcome?.playerId).toBe(candidate.id);
  const outcome = page.getByRole('region', { name: 'Resultado del titular elegido' });
  await expect(outcome).toBeVisible();
  await expectNoAxeViolations(page);
  const evidence = required(required(completed.lastBlockSummary).keyStarterOutcome);
  if (evidence.absenceReason === null) {
    expect(evidence.starterIds).toContain(candidate.id);
    await expect(outcome).toContainText('Jugó de titular');
  } else expect(evidence.starterIds).not.toContain(candidate.id);
  await page.reload();
  await expect(outcome).toBeVisible();
  await expectNoHorizontalScroll(page);
});

test('real advance can omit the choice, and a later sale explains a selected reserve absence', async ({
  page,
}) => {
  await start(page);
  await decide(page, 'Contragolpe');
  await expect(
    page.getByRole('button', { name: 'Simular bloque sin elegir titular' }),
  ).toBeEnabled();
  const first = await advance(page);
  expect(first.lastBlockSummary?.keyStarterOutcome ?? null).toBeNull();
  await decide(page);
  const third = await advance(page);
  // The winter transfer dilemma can remove one of the server's captured reserves.
  const candidate = third.keyStarter?.candidates.find(
    (p) => p.id === 'tfc-18' || p.id === 'tfc-17',
  );
  expect(candidate, JSON.stringify(third.keyStarter)).toBeDefined();
  await page.locator(`input[type="radio"][value="${required(candidate).id}"]`).check();
  await page.getByRole('button', { name: 'Confirmar titular' }).click();
  await expect(
    page.getByText(`Titular confirmado: ${required(candidate).displayName}`),
  ).toBeVisible();
  await decide(
    page,
    required(candidate).id === 'tfc-18'
      ? 'Vender a un suplente a Mock City'
      : 'Vender a otro suplente fuera de la liga',
  );
  const completed = await advance(page);
  expect(completed.lastBlockSummary?.keyStarterOutcome).toMatchObject({
    playerId: required(candidate).id,
    absenceReason: 'not_in_squad',
  });
  const outcome = page.getByRole('region', { name: 'Resultado del titular elegido' });
  await expect(outcome).toContainText('Ya no estaba en la plantilla');
  await expect(outcome.getByText('Once real')).toBeVisible();
});

function required<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) throw new Error('Expected test fixture value');
  return value;
}
