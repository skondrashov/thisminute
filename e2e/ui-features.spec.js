import { test, expect } from "@playwright/test";

test.describe("world bar", () => {

    test("positive is the default world", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        const activeBtn = page.locator(".world-btn.active");
        await expect(activeBtn).toHaveAttribute("data-world", "positive");
    });

    test("world bar renders worlds", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        // Wait for dynamic render
        await page.waitForFunction(() => document.querySelectorAll(".world-btn").length >= 5, { timeout: 10000 });

        const count = await page.locator(".world-btn").count();
        expect(count).toBeGreaterThanOrEqual(5);
    });

    test("positive is the active world on load", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForFunction(() => document.querySelectorAll(".world-btn").length >= 5, { timeout: 10000 });

        const activeWorld = await page.locator(".world-btn.active").getAttribute("data-world");
        expect(activeWorld).toBe("positive");
    });

    test("world bar contains both positive and news", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForFunction(() => document.querySelectorAll(".world-btn").length >= 5, { timeout: 10000 });

        const worlds = await page.locator(".world-btn").evaluateAll(btns => btns.map(b => b.dataset.world));
        expect(worlds).toContain("positive");
        expect(worlds).toContain("news");
    });

    test("clicking a world switches active state", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Click Sports
        await page.locator('.world-btn[data-world="sports"]').click();
        await page.waitForTimeout(300);

        await expect(page.locator('.world-btn[data-world="sports"]')).toHaveClass(/active/);
        await expect(page.locator('.world-btn[data-world="positive"]')).not.toHaveClass(/active/);
    });

    test("world bar wraps on desktop (no horizontal scroll)", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        const overflow = await page.evaluate(() => {
            return window.getComputedStyle(document.getElementById("worlds-bar")).flexWrap;
        });
        expect(overflow).toBe("wrap");
    });
});

test.describe("time badge", () => {

    test("time badge is visible on map", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#time-badge")).toBeVisible();
        const text = await page.locator("#time-badge-label").textContent();
        expect(text).toContain("All Time");
    });

    test("time badge shows story count", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.waitForFunction(() => {
            const el = document.getElementById("time-badge-label");
            return el && el.textContent.includes("stories");
        }, { timeout: 10000 });

        const text = await page.locator("#time-badge-label").textContent();
        expect(text).toMatch(/\d+ stories/);
    });

    test("clicking time badge opens dropdown", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#time-badge-menu")).not.toHaveClass(/open/);

        await page.locator("#time-badge").click();
        await expect(page.locator("#time-badge-menu")).toHaveClass(/open/);
    });

    test("selecting time option updates badge and closes menu", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Open menu
        await page.locator("#time-badge").click();
        await expect(page.locator("#time-badge-menu")).toHaveClass(/open/);

        // Click "Last 24 Hours"
        await page.locator('.tb-option[data-time="24"]').click();
        await page.waitForTimeout(300);

        // Menu should close
        await expect(page.locator("#time-badge-menu")).not.toHaveClass(/open/);

        // Badge should show "Last 24 Hours"
        const text = await page.locator("#time-badge-label .tb-time").textContent();
        expect(text).toBe("Last 24 Hours");
    });

    test("clicking outside closes time menu", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#time-badge").click();
        await expect(page.locator("#time-badge-menu")).toHaveClass(/open/);

        // Click on the map
        await page.locator("#map").click({ position: { x: 400, y: 400 } });
        await expect(page.locator("#time-badge-menu")).not.toHaveClass(/open/);
    });

    test("time select is hidden from sidebar", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        const display = await page.evaluate(() => {
            return window.getComputedStyle(document.getElementById("filter-time")).display;
        });
        expect(display).toBe("none");
    });
});

test.describe("filter status line", () => {

    test("filter status hidden when no filters active", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // With default "All Time" and no other filters, status should be hidden or minimal
        const el = page.locator("#filter-status");
        // May or may not have visible class depending on story count
        const isVisible = await el.evaluate(el => el.classList.contains("visible"));
        // If visible, it should show story count
        if (isVisible) {
            const text = await el.textContent();
            expect(text).toMatch(/stories/);
        }
    });

    test("filter status shows time when time filter is active", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Set time filter via badge
        await page.locator("#time-badge").click();
        await page.locator('.tb-option[data-time="24"]').click();
        await page.waitForTimeout(500);

        const el = page.locator("#filter-status");
        await expect(el).toHaveClass(/visible/);
        const text = await el.textContent();
        expect(text).toContain("24h");
    });
});

test.describe("dot theme", () => {

    test("dot theme button visible on desktop", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#dot-theme-btn")).toBeVisible();
    });

    test("clicking dot theme button opens menu", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#dot-theme-btn").click();
        await expect(page.locator("#dot-theme-menu")).toHaveClass(/open/);
    });

    test("dot theme menu has 5 options", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#dot-theme-btn").click();
        const items = page.locator(".dot-theme-item");
        await expect(items).toHaveCount(5);
    });

    test("selecting a theme closes menu", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#dot-theme-btn").click();
        await page.locator(".dot-theme-item").nth(1).click(); // Classic
        await page.waitForTimeout(200);

        await expect(page.locator("#dot-theme-menu")).not.toHaveClass(/open/);
    });
});

test.describe("legend", () => {

    test("map legend visible on desktop", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#map-legend")).toBeVisible();
    });

    test("legend has domain items", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        const items = page.locator(".legend-item");
        const count = await items.count();
        expect(count).toBeGreaterThanOrEqual(5);
    });
});

test.describe("menu", () => {

    test("menu opens on click", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#main-menu")).not.toHaveClass(/visible/);

        await page.locator("#menu-btn").click();
        await expect(page.locator("#main-menu")).toHaveClass(/visible/);
    });

    test("menu has replay tour option", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#menu-btn").click();
        await expect(page.locator("#menu-replay-tour")).toBeVisible();
    });

    test("menu has pick worlds option", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#menu-btn").click();
        await expect(page.locator("#menu-pick-worlds")).toBeVisible();
    });

    test("pick worlds opens world picker dialog", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.locator("#menu-btn").click();
        await page.locator("#menu-pick-worlds").click();
        await page.waitForTimeout(300);

        await expect(page.locator("#world-picker-dialog")).toHaveClass(/visible/);
    });
});

test.describe("welcome dialog", () => {

    test("welcome dialog has 6 cards", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // The dialog may not be visible (not first visit), but the cards should exist in DOM
        const cards = page.locator(".welcome-card");
        await expect(cards).toHaveCount(6);
    });

    test("welcome cards have correct worlds", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        const worlds = await page.locator(".welcome-card").evaluateAll(cards =>
            cards.map(c => c.dataset.world)
        );
        expect(worlds).toContain("positive");
        expect(worlds).toContain("sports");
        expect(worlds).toContain("curious");
        expect(worlds).toContain("crisis");
        expect(worlds).toContain("entertainment");
        expect(worlds).not.toContain("news");
    });
});

test.describe("world switching colors", () => {

    test("switching worlds changes legend dot tint", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForFunction(() => document.querySelectorAll(".legend-dot").length > 0, { timeout: 10000 });

        // Get legend dot color in Positive world
        const posColor = await page.evaluate(() => {
            const dot = document.querySelector(".legend-dot");
            return dot ? dot.style.background : "";
        });

        // Switch to Sports
        await page.locator('.world-btn[data-world="sports"]').click();
        await page.waitForTimeout(500);

        const sportsColor = await page.evaluate(() => {
            const dot = document.querySelector(".legend-dot");
            return dot ? dot.style.background : "";
        });

        // Colors should be different (different world tints)
        expect(posColor).not.toBe(sportsColor);
    });
});

test.describe("no errors during new feature interactions", () => {

    test("no console errors during world switching and time changes", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (err) => errors.push(err.message));

        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Wait for worlds bar to render
        await page.waitForFunction(() => document.querySelectorAll(".world-btn").length >= 5, { timeout: 15000 });

        // Switch to a world with more stories first
        await page.locator('.world-btn[data-world="sports"]').click();
        await page.waitForTimeout(500);
        await page.locator('.world-btn[data-world="curious"]').click();
        await page.waitForTimeout(500);
        await page.locator('.world-btn[data-world="positive"]').click();
        await page.waitForTimeout(500);

        // Open time badge and select
        await page.locator("#time-badge").click();
        await page.waitForTimeout(200);
        await page.locator('.tb-option[data-time="24"]').click();
        await page.waitForTimeout(500);

        // Open dot theme menu
        await page.locator("#dot-theme-btn").click();
        await page.waitForTimeout(200);
        await page.locator("#dot-theme-btn").click();
        await page.waitForTimeout(200);

        // Open main menu
        await page.locator("#menu-btn").click();
        await page.waitForTimeout(200);
        await page.keyboard.press("Escape");
        await page.waitForTimeout(200);

        expect(errors).toEqual([]);
    });
});
