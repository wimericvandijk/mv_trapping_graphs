export default async function run(page) {
  await page.getByRole('button', { name: 'Expand' }).nth(1).click()
  await page.waitForFunction(() => !document.getElementById('chart-overlay').hidden)
  const overlayToolbarHidden = await page.locator('#overlay-comparison-toolbar').evaluate((node) => node.hidden)
  const overlayButtons = await page.locator('#overlay-year-toggle-group .year-toggle').count()
  const overlayTitle = await page.locator('#overlay-title').innerText()
  return { overlayToolbarHidden, overlayButtons, overlayTitle }
}
