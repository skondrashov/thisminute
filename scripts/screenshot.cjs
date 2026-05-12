// Usage: node scripts/screenshot.cjs <output-path>
const { chromium } = require('playwright');
const path = require('path');

const outPath = process.argv[2] || 'C:/Users/tkond/AppData/Local/Temp/thisminute-screenshot.png';

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => {
        const el = document.getElementById('stat-total');
        return el && el.textContent && el.textContent !== '--';
    }, { timeout: 15000 });

    // Let map + content fully render
    await page.waitForTimeout(2500);

    // If --dropdown flag, open the preset dropdown instead
    if (process.argv.includes('--dropdown')) {
        const trigger = await page.$('#preset-dropdown-trigger');
        if (trigger) {
            await trigger.click();
            await page.waitForTimeout(500);
        }
    } else {
        // Expand first situation for richer visual
        const sit = await page.waitForSelector('.situation-item', { timeout: 10000 }).catch(() => null);
        if (sit) {
            await sit.click();
            await page.waitForTimeout(800);
        }
    }

    // Check if --sidebar flag to crop to sidebar only
    if (process.argv.includes('--sidebar')) {
        const sidebar = await page.$('#sidebar');
        if (sidebar) {
            await sidebar.screenshot({ path: outPath });
        } else {
            await page.screenshot({ path: outPath, fullPage: false });
        }
    } else {
        await page.screenshot({ path: outPath, fullPage: false });
    }
    console.log(`Saved: ${outPath}`);
    await browser.close();
})();
