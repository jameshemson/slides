import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { ROOT } from './utils.js';

// Regression gate for check-sync.js version-drift detection. We temporarily
// mutate the Codex plugin.json version, spawn check-sync.js synchronously
// (so the test cannot proceed past spawnSync until exit), and restore the
// original content in a try/finally. Because spawnSync is synchronous, the
// only way the restore can fail to run is if Node itself dies between the
// write and the spawn — vanishingly unlikely for a local test. If it ever
// happens, `git checkout -- plugins/slides/.codex-plugin/plugin.json`
// restores the file.

const pluginPath = join(ROOT, 'plugins/slides/.codex-plugin/plugin.json');

test('check-sync exits 1 when plugin.json versions diverge', () => {
  const original = readFileSync(pluginPath, 'utf8');
  try {
    const parsed = JSON.parse(original);
    parsed.version = '99.99.99';
    writeFileSync(pluginPath, JSON.stringify(parsed, null, 2) + '\n', 'utf8');

    const result = spawnSync(
      'node',
      [join(ROOT, 'scripts/check-sync.js')],
      { cwd: ROOT, encoding: 'utf8' },
    );

    assert.notEqual(result.status, 0, 'check-sync should exit non-zero on version drift');
    const combined = (result.stdout || '') + (result.stderr || '');
    assert.match(combined, /Version drift/, 'error message should mention "Version drift"');
    assert.match(combined, /99\.99\.99/, 'error message should quote the mismatched version');
  } finally {
    writeFileSync(pluginPath, original, 'utf8');
  }
});
