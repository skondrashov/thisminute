import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./e2e",
    timeout: 120000,
    retries: 1,
    use: {
        baseURL: process.env.TEST_URL || "https://thisminute.org",
        headless: true,
        viewport: { width: 1280, height: 800 },
        screenshot: "only-on-failure",
    },
    projects: [
        {
            name: "chromium",
            use: { browserName: "chromium" },
        },
    ],
});
