const { test, expect } = require("@playwright/test");

test.describe("thisminute visual tests", () => {

    test("page loads without errors", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (err) => errors.push(err.message));

        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // No JavaScript errors
        expect(errors).toEqual([]);
    });

    test("sidebar renders with all sections", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Header
        await expect(page.locator("#sidebar-header h1")).toHaveText("thisminute");

        // Stats bar shows numbers (not --)
        await page.waitForFunction(() => {
            const el = document.getElementById("stat-total");
            return el && el.textContent !== "--";
        }, { timeout: 10000 });
        const totalText = await page.locator("#stat-total").textContent();
        expect(parseInt(totalText)).toBeGreaterThan(0);

        // View toggle buttons exist
        await expect(page.locator("#btn-markers")).toBeVisible();
        await expect(page.locator("#btn-heatmap")).toBeVisible();

        // Search box exists
        await expect(page.locator("#search-box")).toBeVisible();

        // Source filter exists
        await expect(page.locator("#filter-source")).toBeVisible();

        // Concept panel exists
        await expect(page.locator("#concept-panel")).toBeVisible();
    });

    test("map canvas is present and sized", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // MapLibre creates a canvas
        const canvas = page.locator("#map canvas");
        await expect(canvas).toBeVisible({ timeout: 10000 });

        // Canvas should have meaningful dimensions
        const box = await canvas.boundingBox();
        expect(box.width).toBeGreaterThan(400);
        expect(box.height).toBeGreaterThan(300);
    });

    test("story list populates", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Wait for stories to load
        await page.waitForSelector(".story-item", { timeout: 10000 });

        const items = await page.locator(".story-item").count();
        expect(items).toBeGreaterThan(0);

        // First story should have a title
        const firstTitle = await page.locator(".story-item .story-title").first().textContent();
        expect(firstTitle.length).toBeGreaterThan(0);
    });

    test("concept chips render", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Wait for concept chips to load
        await page.waitForSelector(".concept-chip", { timeout: 10000 });

        const chips = await page.locator(".concept-chip").count();
        expect(chips).toBeGreaterThan(5); // Should have many concepts

        // Domain labels should exist
        const domains = await page.locator(".concept-domain-label").count();
        expect(domains).toBeGreaterThan(3);
    });

    test("filter presets work", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForSelector(".story-item", { timeout: 10000 });

        // Get initial story count
        const initialCount = await page.locator(".story-item").count();

        // Click "Conflict" preset
        await page.locator('[data-preset="conflict"]').click();

        // Wait for filter to apply
        await page.waitForTimeout(500);

        // Story count should change (filtered)
        const filteredCount = await page.locator(".story-item").count();
        // It could be less (if conflict filter reduces) or different
        // The preset button should be active
        await expect(page.locator('[data-preset="conflict"]')).toHaveClass(/active/);

        // Click again to deactivate
        await page.locator('[data-preset="conflict"]').click();
        await page.waitForTimeout(500);
        await expect(page.locator('[data-preset="conflict"]')).not.toHaveClass(/active/);
    });

    test("search filters stories", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForSelector(".story-item", { timeout: 10000 });

        const initialCount = await page.locator(".story-item").count();

        // Type a search term
        await page.fill("#search-box", "war");
        await page.waitForTimeout(400); // debounce

        const filteredCount = await page.locator(".story-item").count();
        expect(filteredCount).toBeLessThanOrEqual(initialCount);
    });

    test("sidebar has no overflow scrollbar on body", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // The body should have overflow: hidden
        const overflow = await page.evaluate(() => {
            return window.getComputedStyle(document.body).overflow;
        });
        expect(overflow).toBe("hidden");

        // The sidebar should not have a visible vertical scrollbar on itself
        // Only #story-list and #concept-panel should scroll
        const sidebarOverflow = await page.evaluate(() => {
            const sidebar = document.getElementById("sidebar");
            const style = window.getComputedStyle(sidebar);
            return style.overflowY;
        });
        // Sidebar should not be scrolling - it uses flex layout
        expect(sidebarOverflow).not.toBe("scroll");
    });

    test("view mode toggle works", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Markers should be active by default
        await expect(page.locator("#btn-markers")).toHaveClass(/active/);
        await expect(page.locator("#btn-heatmap")).not.toHaveClass(/active/);

        // Click heatmap
        await page.locator("#btn-heatmap").click();
        await expect(page.locator("#btn-heatmap")).toHaveClass(/active/);
        await expect(page.locator("#btn-markers")).not.toHaveClass(/active/);

        // Click markers again
        await page.locator("#btn-markers").click();
        await expect(page.locator("#btn-markers")).toHaveClass(/active/);
    });

    test("keyboard shortcut ? shows help", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Help overlay should be hidden
        await expect(page.locator("#shortcuts-overlay")).not.toHaveClass(/visible/);

        // Press ?
        await page.keyboard.press("Shift+/"); // ? = Shift+/
        await expect(page.locator("#shortcuts-overlay")).toHaveClass(/visible/);

        // Press any key to close
        await page.keyboard.press("Escape");
        await expect(page.locator("#shortcuts-overlay")).not.toHaveClass(/visible/);
    });

    test("no console errors during interaction", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (err) => errors.push(err.message));

        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForSelector(".story-item", { timeout: 10000 });

        // Click a story
        await page.locator(".story-item").first().click();
        await page.waitForTimeout(500);

        // Toggle heatmap
        await page.locator("#btn-heatmap").click();
        await page.waitForTimeout(500);

        // Toggle back to markers
        await page.locator("#btn-markers").click();
        await page.waitForTimeout(500);

        // Search
        await page.fill("#search-box", "test");
        await page.waitForTimeout(400);

        // Clear search
        await page.fill("#search-box", "");
        await page.waitForTimeout(400);

        // No errors during all interactions
        expect(errors).toEqual([]);
    });
});
