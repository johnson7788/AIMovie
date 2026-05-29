import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto('http://localhost:36310/aimovie/#/');
await page.waitForTimeout(3000);

const loginBtn = page.locator('text=一键登录');
await loginBtn.click();
await page.waitForTimeout(2000);

// Screenshot default tab
await page.screenshot({ path: '/tmp/login-tab1.png' });

// Switch to phone login tab
await page.locator('text=手机号登录').click();
await page.waitForTimeout(1000);
await page.screenshot({ path: '/tmp/login-tab2.png' });

// Switch back to account and click wechat
await page.locator('text=账号密码').click();
await page.waitForTimeout(1000);
await page.locator('[alt="微信登录"]').click();
await page.waitForTimeout(2000);
await page.screenshot({ path: '/tmp/login-tab3.png' });

console.log('Screenshots saved');
await browser.close();
