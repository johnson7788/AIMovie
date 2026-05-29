import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto('http://localhost:36310/aimovie/#/');
await page.waitForTimeout(3000);

// Click login button
const loginBtn = page.locator('text=一键登录');
await loginBtn.click();
await page.waitForTimeout(2000);

// Screenshot the modal
const modal = page.locator('.x-login-message-box');
if (await modal.isVisible().catch(() => false)) {
  await modal.screenshot({ path: '/tmp/login-modal.png' });
  console.log('Modal screenshot saved to /tmp/login-modal.png');
} else {
  await page.screenshot({ path: '/tmp/login-full.png', fullPage: false });
  console.log('Full page screenshot saved to /tmp/login-full.png');
}

// Also capture page screenshot
await page.screenshot({ path: '/tmp/login-page.png', fullPage: false });
console.log('Page screenshot saved to /tmp/login-page.png');

await browser.close();
