import { expect, test } from '@playwright/test';

test('home loads on a mobile viewport and shows the title', async ({ page, isMobile }) => {
  expect(isMobile).toBe(true);

  await page.goto('/');

  await expect(page).toHaveTitle('Míster Histórico');
  await expect(page.getByRole('heading', { level: 1, name: 'Míster Histórico' })).toBeVisible();
  await expect(page.getByText('¿Lo habrías hecho mejor que el míster?')).toBeVisible();
});
