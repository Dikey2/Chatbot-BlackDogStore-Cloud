import { defineConfig } from "@playwright/test";

// Las pruebas usan el stack ya levantado con `docker compose up -d`.
export default defineConfig({
  testDir: "./e2e",
  // Un solo worker: las pruebas comparten el rate limit de autenticación (10/min por IP).
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
  },
});
