// Single source of truth for the four files that carry the release version.
// Both scripts/check-sync.js (pre-build parity assertion) and
// scripts/transformers/manifests.test.js (in-process parity test) import
// from here, so a contributor adding a fifth carrier only updates this file.
export const VERSION_CARRIERS = [
  { path: '.claude-plugin/plugin.json', get: (j) => j.version },
  { path: '.claude-plugin/marketplace.json', get: (j) => j.plugins?.[0]?.version },
  { path: 'plugins/slides/.codex-plugin/plugin.json', get: (j) => j.version },
  { path: 'package.json', get: (j) => j.version },
];
