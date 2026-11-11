import {defineConfig} from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 35000,
  fullyParallel: true,
  workers: 2,
  reporter: [['list'], ['html', {open: 'never'}], ['json', {outputFile: '../../evals/results/playwright.json'}]],
  use: {baseURL: process.env.GIGBID_TEST_URL || 'http://127.0.0.1:8018', trace: 'retain-on-failure'},
  webServer: {
    command: 'python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8018',
    cwd: '../..',
    env: {GIGBID_ENABLE_TEST_CONTROLS:'1',GIGBID_DEMO_ACCESS:'1',GIGBID_STATE_DIR:'.state/playwright'},
    url: 'http://127.0.0.1:8018/health',
    timeout: 30000,
    reuseExistingServer: false,
  },
})
