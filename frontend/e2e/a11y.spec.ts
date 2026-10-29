import { expect, test, type Page } from '@playwright/test';

import {
  expectFocusInsidePage,
  expectNoAxeViolations,
  expectNoHorizontalScroll,
  tabTo,
} from './support/a11y';

// Served by the MSW dev server of playwright.config.ts: the fictional Test FC season, no backend.
const MOCKED_BASE_URL = 'http://localhost:5174';
const MAX_BLOCKS = 10;

async function expectAccessibleScreen(page: Page): Promise<void> {
  await expectNoAxeViolations(page);
  await expectNoHorizontalScroll(page);
}

for (const colorScheme of ['light', 'dark'] as const) {
  test.describe(`${colorScheme} theme at 360 px`, () => {
    test.use({ baseURL: MOCKED_BASE_URL, colorScheme, viewport: { width: 360, height: 740 } });

    test('a whole run is playable with the keyboard, with no axe violations or sideways scroll', async ({
      page,
    }) => {
      await page.goto('/');
      const choose = page.getByRole('button', { name: /^Elegir Test FC/ });
      await expect(choose).toBeVisible();
      await expectAccessibleScreen(page);

      await tabTo(page, choose);
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/equipo\//);
      await expectFocusInsidePage(page);
      const start = page.getByRole('button', { name: 'Empezar' });
      await expect(start).toBeVisible();
      await expectAccessibleScreen(page);

      await tabTo(page, start);
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/partida\//);
      await expectFocusInsidePage(page);
      const simulate = page.getByRole('button', { name: 'Simular bloque' });
      await expect(simulate).toBeVisible();
      await expectAccessibleScreen(page);

      const finalTitle = page.getByRole('heading', { level: 1, name: 'Final de la partida' });
      for (let block = 1; block <= MAX_BLOCKS; block += 1) {
        const optionGroups = page.getByRole('group', { name: /^Opciones/ });
        while (await optionGroups.count()) {
          const group = optionGroups.first();
          const name = await group.getAttribute('aria-label');
          await tabTo(page, group.getByRole('button').first());
          await page.keyboard.press('Space');
          await tabTo(page, page.getByRole('button', { name: /^Confirmar:/ }).first());
          await page.keyboard.press('Enter');
          await expect(page.getByRole('group', { name: name ?? '', exact: true })).toHaveCount(0);
          await expect(page.getByRole('heading', { name: 'Decisión confirmada' })).toBeFocused();
        }
        await tabTo(page, simulate);
        await page.keyboard.press('Enter');
        // The block summary (or the final page) takes the focus once the block is simulated.
        await expect(page.locator(':focus')).toHaveRole('heading');
        const skip = page.getByRole('button', { name: 'Mostrar todos' });
        await expect(skip).toBeVisible();
        await tabTo(page, skip);
        await page.keyboard.press('Enter');
        await expect(skip).toHaveCount(0);
        await expect(simulate.or(finalTitle)).toBeVisible();
        if (await finalTitle.isVisible()) break;
        await expectAccessibleScreen(page);
      }

      await expect(page).toHaveURL(/\/final$/);
      await expect(finalTitle).toBeFocused();
      await expectAccessibleScreen(page);
    });
  });
}
