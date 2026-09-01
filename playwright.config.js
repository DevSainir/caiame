import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end гоняются против настоящего браузера, настоящего API и настоящей базы.
 *
 * Фронтенд поднимается сам, API — нет: он держит соединение с базой, и запуск его отсюда
 * спрятал бы половину настройки в конфиг, где её никто не ищет. Если API не поднят, тесты
 * падают сразу и с понятным текстом.
 */
export default defineConfig({
  testDir: './tests/end-to-end',
  // Их мало и они дорогие: смысл в том, чтобы каждый оправдывал своё существование.
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5174',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev --prefix frontend -- --port 5174 --strictPort',
    url: 'http://localhost:5174',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
