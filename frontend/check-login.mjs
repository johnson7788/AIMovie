import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto('http://localhost:36310/aimovie/#/');
await page.waitForTimeout(3000);

const loginBtn = page.locator('text=一键登录');
await loginBtn.click();
await page.waitForTimeout(2000);

// Get modal element info
const modal = await page.locator('.el-message-box').first();
const className = await modal.evaluate(el => el.className);
const styles = await modal.evaluate(el => {
  const computed = window.getComputedStyle(el);
  return {
    width: computed.width,
    maxWidth: computed.maxWidth,
    height: computed.height,
    display: computed.display
  };
});

const msgStyles = await page.locator('.el-message-box__message').first().evaluate(el => {
  const computed = window.getComputedStyle(el);
  return {
    width: computed.width,
    height: computed.height
  };
});

const loginStyles = await page.locator('.x-login').first().evaluate(el => {
  const computed = window.getComputedStyle(el);
  return {
    width: computed.width,
    height: computed.height
  };
});

console.log('Modal class:', className);
console.log('Modal styles:', JSON.stringify(styles, null, 2));
console.log('Message styles:', JSON.stringify(msgStyles, null, 2));
console.log('Login styles:', JSON.stringify(loginStyles, null, 2));

await browser.close();
