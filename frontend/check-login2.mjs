import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto('http://localhost:36310/aimovie/#/');
await page.waitForTimeout(3000);

const loginBtn = page.locator('text=一键登录');
await loginBtn.click();
await page.waitForTimeout(2000);

const result = await page.evaluate(() => {
  const el = document.querySelector('.el-message-box.x-login-message-box');
  if (!el) return { error: 'not found' };
  
  const computed = window.getComputedStyle(el);
  const propValue = computed.getPropertyValue('--el-messagebox-width');
  
  // Find which stylesheet defines --el-messagebox-width for this element
  let sources = [];
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        if (rule.selectorText && (rule.selectorText.includes('el-message-box') || rule.selectorText.includes('x-login-message-box'))) {
          const text = rule.cssText;
          if (text.includes('--el-messagebox-width')) {
            sources.push({ href: sheet.href || 'inline', selector: rule.selectorText, text: text.substring(0, 200) });
          }
        }
      }
    } catch (e) {}
  }
  
  return {
    propValue,
    className: el.className,
    sources
  };
});

console.log(JSON.stringify(result, null, 2));

await browser.close();
