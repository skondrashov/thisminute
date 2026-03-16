import { test, expect } from "@playwright/test";

// Helper: wait for situations to load in the sidebar
async function waitForSituations(page) {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForFunction(
        () => document.querySelectorAll(".situation-item").length > 0,
        { timeout: 15000 }
    );
}

// Helper: wait for events tab and switch to it
async function switchToEvents(page) {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.locator('.view-btn[data-view="events"]').click();
    await page.waitForFunction(
        () => document.querySelectorAll(".event-item").length > 0,
        { timeout: 15000 }
    );
}

// Helper: expand a situation and get its stories panel
async function expandFirstSituation(page) {
    await waitForSituations(page);
    await page.locator(".situation-item").first().click();
    await page.waitForTimeout(500);
}

// Helper: expand an event and wait for stories to load
async function expandFirstEvent(page) {
    await switchToEvents(page);
    await page.locator(".event-item").first().click();
    await page.waitForTimeout(500);
}

// ─── Situations: share + flag ───────────────────────────────

test.describe("situation actions", () => {

    test("situation has share button when expanded", async ({ page }) => {
        await waitForSituations(page);
        // Expand first situation
        await page.locator(".situation-item").first().click();
        await page.waitForTimeout(300);

        const shareBtn = page.locator(".situation-item.expanded .situation-share-btn");
        await expect(shareBtn).toBeVisible();
    });

    test("situation has feedback button when expanded", async ({ page }) => {
        await waitForSituations(page);
        await page.locator(".situation-item").first().click();
        await page.waitForTimeout(300);

        const feedbackBtn = page.locator(".situation-item.expanded .feedback-btn");
        await expect(feedbackBtn).toBeVisible();
    });

    test("situation share button copies link with situation ID", async ({ page }) => {
        await waitForSituations(page);
        await page.locator(".situation-item").first().click();
        await page.waitForTimeout(300);

        const sitId = await page.locator(".situation-item.expanded").getAttribute("data-narrative-id");
        const shareBtn = page.locator(".situation-item.expanded .situation-share-btn");

        // Grant clipboard permission
        await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
        await shareBtn.click();
        await page.waitForTimeout(300);

        const clipboard = await page.evaluate(() => navigator.clipboard.readText());
        expect(clipboard).toContain(`situation=${sitId}`);
    });

    test("situation feedback button opens feedback dialog", async ({ page }) => {
        await waitForSituations(page);
        await page.locator(".situation-item").first().click();
        await page.waitForTimeout(300);

        await page.locator(".situation-item.expanded .feedback-btn").click();
        await page.waitForTimeout(300);

        await expect(page.locator("#feedback-dialog")).toBeVisible();
    });
});

// ─── Events: share + flag ───────────────────────────────────

test.describe("event actions", () => {

    test("event has share button when expanded", async ({ page }) => {
        await switchToEvents(page);
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(300);

        const shareBtn = page.locator(".event-item.expanded .event-share-btn");
        await expect(shareBtn).toBeVisible();
    });

    test("event has feedback button when expanded", async ({ page }) => {
        await switchToEvents(page);
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(300);

        const feedbackBtn = page.locator(".event-item.expanded .feedback-btn");
        await expect(feedbackBtn).toBeVisible();
    });

    test("event share button copies link with event ID", async ({ page }) => {
        await switchToEvents(page);
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(300);

        const eventId = await page.locator(".event-item.expanded").getAttribute("data-event-id");
        const shareBtn = page.locator(".event-item.expanded .event-share-btn");

        await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
        await shareBtn.click();
        await page.waitForTimeout(300);

        const clipboard = await page.evaluate(() => navigator.clipboard.readText());
        expect(clipboard).toContain(`event=${eventId}`);
    });

    test("event feedback button opens feedback dialog", async ({ page }) => {
        await switchToEvents(page);
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(300);

        await page.locator(".event-item.expanded .feedback-btn").click();
        await page.waitForTimeout(300);

        await expect(page.locator("#feedback-dialog")).toBeVisible();
    });

    test("event share button has no white background in dark mode", async ({ page }) => {
        await switchToEvents(page);
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(300);

        const bg = await page.locator(".event-item.expanded .event-share-btn").evaluate(
            el => window.getComputedStyle(el).backgroundColor
        );
        // "none" or "transparent" or "rgba(0, 0, 0, 0)" — not white
        expect(bg).toMatch(/^(transparent|rgba\(0,\s*0,\s*0,\s*0\))$/);
    });
});

// ─── Stories: share + flag ──────────────────────────────────

test.describe("story actions", () => {

    test("story card has copy-link button", async ({ page }) => {
        await expandFirstSituation(page);
        // Wait for stories panel to load
        await page.waitForFunction(
            () => document.querySelectorAll(".info-card").length > 0,
            { timeout: 15000 }
        );

        const copyBtn = page.locator(".info-card .info-card-copy").first();
        await expect(copyBtn).toBeVisible();
    });

    test("story card has feedback button", async ({ page }) => {
        await expandFirstSituation(page);
        await page.waitForFunction(
            () => document.querySelectorAll(".info-card").length > 0,
            { timeout: 15000 }
        );

        const feedbackBtn = page.locator(".info-card .info-card-feedback").first();
        await expect(feedbackBtn).toBeVisible();
    });

    test("story card has read-full-story link", async ({ page }) => {
        await expandFirstSituation(page);
        await page.waitForFunction(
            () => document.querySelectorAll(".info-card").length > 0,
            { timeout: 15000 }
        );

        const link = page.locator(".info-card .info-card-link").first();
        await expect(link).toBeVisible();
        const href = await link.getAttribute("href");
        expect(href).toBeTruthy();
        expect(href).toMatch(/^https?:\/\//);
    });

    test("story feedback button opens feedback dialog", async ({ page }) => {
        await expandFirstSituation(page);
        await page.waitForFunction(
            () => document.querySelectorAll(".info-card").length > 0,
            { timeout: 15000 }
        );

        await page.locator(".info-card .info-card-feedback").first().click();
        await page.waitForTimeout(300);

        await expect(page.locator("#feedback-dialog")).toBeVisible();
    });
});

// ─── Preset share button ────────────────────────────────────

test.describe("preset share", () => {

    test("preset share button exists", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await expect(page.locator("#preset-share-btn")).toBeVisible();
    });

    test("preset share copies current URL to clipboard", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
        await page.locator("#preset-share-btn").click();
        await page.waitForTimeout(300);

        const clipboard = await page.evaluate(() => navigator.clipboard.readText());
        expect(clipboard).toContain("thisminute");
    });

    test("preset share includes active preset in URL", async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");

        // Switch to Sports
        await page.locator('.preset-btn[data-world="sports"]').click();
        await page.waitForTimeout(300);

        await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
        await page.locator("#preset-share-btn").click();
        await page.waitForTimeout(300);

        const clipboard = await page.evaluate(() => navigator.clipboard.readText());
        expect(clipboard).toContain("world=sports");
    });
});

// ─── Deep linking ───────────────────────────────────────────

test.describe("deep links", () => {

    test("situation deep link loads the correct situation", async ({ page }) => {
        // First get a valid situation ID
        await waitForSituations(page);
        const sitId = await page.locator(".situation-item").first().getAttribute("data-narrative-id");

        // Navigate to the deep link
        await page.goto(`/?situation=${sitId}`);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(1000);

        // The situation should be active/expanded
        const activeSit = page.locator(`.situation-item[data-narrative-id="${sitId}"]`);
        await expect(activeSit).toHaveClass(/active|expanded/);
    });

    test("event deep link loads with event param", async ({ page }) => {
        // Get a valid event ID
        await switchToEvents(page);
        const eventId = await page.locator(".event-item").first().getAttribute("data-event-id");

        // Navigate to the deep link
        await page.goto(`/?event=${eventId}`);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(1000);

        // The event view should be active
        const url = page.url();
        expect(url).toContain(`event=${eventId}`);
    });

    test("preset deep link sets correct preset", async ({ page }) => {
        await page.goto("/?world=sports");
        await page.waitForLoadState("networkidle");
        await page.waitForFunction(
            () => document.querySelectorAll(".preset-btn").length >= 5,
            { timeout: 10000 }
        );

        const activeWorld = await page.locator(".preset-btn.active").getAttribute("data-world");
        expect(activeWorld).toBe("sports");
    });
});

// ─── No console errors during entity interactions ───────────

test.describe("no errors during entity actions", () => {

    test("no console errors when interacting with situations, events, and stories", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (err) => errors.push(err.message));

        await page.goto("/");
        await page.waitForLoadState("networkidle");
        await page.waitForFunction(
            () => document.querySelectorAll(".situation-item").length > 0,
            { timeout: 15000 }
        );

        // Expand a situation
        await page.locator(".situation-item").first().click();
        await page.waitForTimeout(500);

        // Click share on situation (may fail clipboard — that's ok)
        await page.locator(".situation-item.expanded .situation-share-btn").click({ timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(200);

        // Click feedback on situation
        await page.locator(".situation-item.expanded .feedback-btn").click({ timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(200);

        // Close feedback dialog if open
        await page.keyboard.press("Escape");
        await page.waitForTimeout(200);

        // Switch to events
        await page.locator('.view-btn[data-view="events"]').click();
        await page.waitForFunction(
            () => document.querySelectorAll(".event-item").length > 0,
            { timeout: 15000 }
        );
        await page.waitForTimeout(300);

        // Expand an event
        await page.locator(".event-item").first().click();
        await page.waitForTimeout(500);

        // Click share on event
        await page.locator(".event-item.expanded .event-share-btn").click({ timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(200);

        // Click feedback on event
        await page.locator(".event-item.expanded .feedback-btn").click({ timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(200);

        expect(errors).toEqual([]);
    });
});
