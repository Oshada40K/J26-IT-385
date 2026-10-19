import { rmSync } from 'node:fs'

// Remove the per-run backend data folder created by playwright.config.js.
export default function teardown() {
  try { rmSync(process.env.E2E_DATA_DIR, { recursive: true, force: true }) }
  catch { /* a file is still locked; the OS temp dir cleans up */ }
}
