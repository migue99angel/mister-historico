import { expect, test, type Locator, type Page } from '@playwright/test';

import { expectNoAxeViolations, expectNoHorizontalScroll, tabTo } from './support/a11y';

async function startRun(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /^Elegir Test FC/ }).click();
  await page.getByRole('button', { name: 'Empezar' }).click();
  await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeVisible();
}

async function toggleWithKeyboard(page: Page, summary: Locator) {
  await tabTo(page, summary);
  await page.keyboard.press('Enter');
}

for (const width of [390, 412, 1280]) {
  test.describe(`coach layout at ${String(width)} px`, () => {
    test.use({ baseURL: 'http://localhost:5174', viewport: { width, height: 900 } });

    test('consults the team and decides with keyboard, long text and enlarged type', async ({
      page,
    }) => {
      await startRun(page);
      const panel = page.getByRole('complementary', { name: 'Panel del equipo' });
      const decisions = page.getByRole('region', { name: 'Decisiones del bloque' });
      await expect(panel).toHaveCount(1);
      const panelBox = await panel.boundingBox();
      const decisionsBox = await decisions.boundingBox();
      expect(panelBox).not.toBeNull();
      expect(decisionsBox).not.toBeNull();
      if (width === 1280) {
        expect((panelBox?.x ?? 0) + (panelBox?.width ?? 0)).toBeLessThanOrEqual(
          decisionsBox?.x ?? 0,
        );
      } else {
        expect((panelBox?.y ?? 0) + (panelBox?.height ?? 0)).toBeLessThanOrEqual(
          decisionsBox?.y ?? 0,
        );
      }
      const squad = panel.locator('summary').filter({ hasText: /^Plantilla/ });
      await toggleWithKeyboard(page, squad);
      await expect(panel.getByText(/Valoración:/).first()).toBeVisible();
      await page.keyboard.press('Space');
      await expect(squad).toBeFocused();
      await expect(panel.getByText(/Valoración:/).first()).not.toBeVisible();
      await toggleWithKeyboard(page, panel.locator('summary').filter({ hasText: 'Clasificación' }));
      await expect(panel.getByText(/al cerrar el primer bloque/)).toBeVisible();
      await tabTo(page, panel.getByRole('button', { name: 'Volver a decisiones' }));
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeFocused();
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeInViewport();

      while (await page.getByRole('group', { name: /^Opciones/ }).count()) {
        await tabTo(
          page,
          page
            .getByRole('group', { name: /^Opciones/ })
            .first()
            .getByRole('button')
            .first(),
        );
        await page.keyboard.press('Space');
        await tabTo(page, page.getByRole('button', { name: /^Confirmar:/ }).first());
        await page.keyboard.press('Enter');
        await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
      }
      await tabTo(page, page.getByRole('button', { name: 'Simular bloque' }));
      await page.keyboard.press('Enter');
      const skip = page.getByRole('button', { name: 'Mostrar todos' });
      await expect(skip).toBeInViewport();
      await expect(page.getByRole('complementary')).toHaveCount(0);
      await tabTo(page, page.getByRole('button', { name: 'Ir a decisiones' }));
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeFocused();
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeInViewport();
      await toggleWithKeyboard(page, panel.locator('summary').filter({ hasText: 'Clasificación' }));
      await expect(panel.getByRole('table', { name: 'Liga Test' })).toBeVisible();
      await toggleWithKeyboard(
        page,
        panel.locator('summary').filter({ hasText: 'Estado y lesiones' }),
      );
      await expect(panel.getByRole('heading', { name: 'Lesiones actuales' })).toBeVisible();
      await toggleWithKeyboard(page, squad);

      // Stress only presentation with synthetic text; no real club content or API changes.
      await panel
        .getByText(/Valoración:/)
        .first()
        .evaluate((node) => {
          (node as unknown as { textContent: string }).textContent = 'JugadorSintético'.repeat(20);
        });
      await panel
        .getByRole('rowheader')
        .first()
        .evaluate((node) => {
          (node as unknown as { textContent: string }).textContent = 'EquipoSintético'.repeat(20);
        });
      await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      await expectNoHorizontalScroll(page);
      await expectNoAxeViolations(page);
      if (width === 1280) {
        // A 1280 px desktop zoomed to 200% has 640 CSS pixels for reflow.
        await page.addStyleTag({ content: 'html { font-size: 100%; }' });
        await page.setViewportSize({ width: 640, height: 900 });
        await expectNoHorizontalScroll(page);
      }
      await tabTo(page, panel.getByRole('button', { name: 'Volver a decisiones' }));
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeFocused();
      await expect(page.getByRole('heading', { name: 'Decisiones del bloque' })).toBeInViewport();
    });
  });
}

for (const width of [390, 412]) {
  test.describe(`reveal controls while scrolling at ${String(width)} px`, () => {
    test.use({ baseURL: 'http://localhost:5175', viewport: { width, height: 700 } });

    test('keeps both controls fully visible while the result list grows and scrolls', async ({
      page,
    }) => {
      await page.clock.install();
      await startRun(page);
      while (await page.getByRole('group', { name: /^Opciones/ }).count()) {
        await page
          .getByRole('group', { name: /^Opciones/ })
          .first()
          .getByRole('button')
          .first()
          .click();
        await page
          .getByRole('button', { name: /^Confirmar:/ })
          .first()
          .click();
        await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
      }
      await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      // Freeze before the advance: timers are stepped without racing the short reveal.
      await page.clock.pauseAt(await page.evaluate(() => Date.now() + 100));
      const advanced = page.waitForResponse((response) =>
        /\/api\/runs\/[^/]+\/advance$/.test(response.url()),
      );
      await page.getByRole('button', { name: 'Simular bloque' }).click();
      await advanced;
      await page.clock.runFor(0);
      const summary = page.getByRole('region', { name: 'Resumen del bloque' });
      const dates = summary.getByRole('heading', { level: 3 });
      const skip = summary.getByRole('button', { name: 'Mostrar todos' });
      const decisions = summary.getByRole('button', { name: 'Ir a decisiones' });
      await expect(dates).toHaveCount(0);
      // The real synthetic season has five dates, so the list can grow while still revealing.
      await page.clock.runFor(2100);
      await expect(dates).toHaveCount(3);
      const beforeScroll = await page.evaluate(
        () => (globalThis as unknown as { scrollY: number }).scrollY,
      );
      await page.mouse.wheel(0, 700);
      await page.clock.runFor(100);
      await expect
        .poll(() => page.evaluate(() => (globalThis as unknown as { scrollY: number }).scrollY))
        .toBeGreaterThan(beforeScroll);
      await expect(
        summary.getByRole('heading', { name: 'Resumen del bloque' }),
      ).not.toBeInViewport();
      await expect(skip).toBeInViewport({ ratio: 1 });
      await expect(decisions).toBeInViewport({ ratio: 1 });
      await page.clock.runFor(600);
      await expect(dates).toHaveCount(4);
      await expect(skip).toBeInViewport({ ratio: 1 });
      await expect(decisions).toBeInViewport({ ratio: 1 });
      await expectNoHorizontalScroll(page);
      await skip.click();
      await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeFocused();
      await expect(page.getByRole('heading', { name: 'Resumen del bloque' })).toBeInViewport();
    });
  });
}

test.describe('reveal focus with enlarged text', () => {
  test.use({ baseURL: 'http://localhost:5174', viewport: { width: 390, height: 700 } });

  for (const completion of ['skip', 'automatic']) {
    test(`keeps the summary in view after ${completion} completion restores the mobile panel`, async ({
      page,
    }) => {
      await startRun(page);
      while (await page.getByRole('group', { name: /^Opciones/ }).count()) {
        await page
          .getByRole('group', { name: /^Opciones/ })
          .first()
          .getByRole('button')
          .first()
          .click();
        await page
          .getByRole('button', { name: /^Confirmar:/ })
          .first()
          .click();
        await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
      }
      await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      await page.getByRole('button', { name: 'Simular bloque' }).click();
      const skip = page.getByRole('button', { name: 'Mostrar todos' });
      await expect(skip).toBeVisible();
      if (completion === 'skip') await skip.click();
      else await expect(skip).toHaveCount(0);
      const summary = page.getByRole('heading', { name: 'Resumen del bloque' });
      await expect(summary).toBeFocused();
      await expect(summary).toBeInViewport();
    });
  }
});
