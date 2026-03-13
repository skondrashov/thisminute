const { chromium } = require('playwright');
(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => {
        const el = document.getElementById('stat-total');
        return el && el.textContent && el.textContent !== '--';
    }, { timeout: 15000 });

    // Expand first situation
    const sit = await page.waitForSelector('.situation-item', { timeout: 10000 });
    await sit.click();
    await page.waitForTimeout(1500);

    // Screenshot just the sidebar area, cropped
    const sidebar = await page.$('#sidebar');
    await sidebar.screenshot({ path: 'C:/Users/tkond/AppData/Local/Temp/thisminute-sidebar.png' });

    await browser.close();
})();
