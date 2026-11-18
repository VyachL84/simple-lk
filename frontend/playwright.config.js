import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  reporter: "list",
  timeout: 30000,
  use: {
    baseURL: `http://127.0.0.1:${process.env.BURO_TEST_PORT || 8080}`,
    viewport: { width: 1366, height: 900 },
    launchOptions: { executablePath: process.env.CHROMIUM_PATH || undefined },
    screenshot: "only-on-failure",
  },
});
