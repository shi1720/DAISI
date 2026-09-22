import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: '*.spec.ts', timeout: 60000, fullyParallel: false,
  workers: 1, retries: 0,
  reporter: [['list'], ['html', { outputFolder: '../output/browser-report', open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:8000', trace: 'retain-on-failure', video: 'on', screenshot: 'only-on-failure', viewport: {width:1440,height:1040} },
  projects: [{name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1040}}}],
  outputDir: '../output/browser-results',
  webServer: { command: '../.venv/bin/python ../scripts/start_app.py', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: !process.env.CI, timeout:30000 },
});
