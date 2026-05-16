import { execSync } from 'child_process';
import { readFileSync } from 'fs';
import { join } from 'path';
import { ROOT } from './transformers/utils.js';
import { PROVIDERS, COMMAND_PROVIDERS } from './transformers/providers.js';
import { VERSION_CARRIERS } from './transformers/version-carriers.js';

// Two checks, in order:
//   1. Version parity between the Claude and Codex plugin manifests.
//      (Reads the two plugin.json files directly; does NOT rely on the build.)
//   2. Structural drift of generated output directories. This loop iterates
//      PROVIDERS.outputDir values — when a new provider is added to
//      providers.js (e.g. codex-plugin → plugins/build/skills), this loop
//      automatically picks it up. That coupling is deliberate: every
//      committed output tree stays in sync with its source by construction.
//
// Note: full version-drift coverage requires running BOTH `npm run check-sync`
// and `npm test` before push. check-sync catches structural drift here;
// manifests.test.js cross-checks the same version parity in-process.

// 1. Version parity pre-check across all release version carriers.
//    A contributor bumping one file must bump all of them; this assertion is
//    mirrored in manifests.test.js via the same VERSION_CARRIERS list.
const versions = VERSION_CARRIERS.map((c) => ({
  path: c.path,
  version: c.get(JSON.parse(readFileSync(join(ROOT, c.path), 'utf8'))),
}));
const unique = [...new Set(versions.map((v) => v.version))];
if (unique.length > 1) {
  console.error('Version drift across release files:');
  for (const { path, version } of versions) {
    console.error(`  ${path}: ${version}`);
  }
  console.error(
    `Bump all ${VERSION_CARRIERS.length} together: ${VERSION_CARRIERS.map((c) => c.path).join(', ')}.`,
  );
  process.exit(1);
}

// 2. Regenerate outputs and diff against git.
console.log('Running build...');
try {
  execSync('node scripts/build.js', { cwd: ROOT, stdio: 'inherit' });
} catch {
  process.exit(1);
}

const outputDirs = [
  ...Object.values(PROVIDERS).map((p) => p.outputDir),
  ...Object.values(COMMAND_PROVIDERS).map((p) => p.outputDir),
];
let dirty = false;

for (const dir of outputDirs) {
  const modified = execSync(`git diff --name-only -- "${dir}"`, { cwd: ROOT })
    .toString()
    .trim();
  const untracked = execSync(
    `git ls-files --others --exclude-standard -- "${dir}"`,
    { cwd: ROOT },
  )
    .toString()
    .trim();

  if (modified) {
    console.error(`Modified (not committed): ${modified}`);
    dirty = true;
  }
  if (untracked) {
    console.error(`Untracked (new files not committed): ${untracked}`);
    dirty = true;
  }
}

if (dirty) {
  console.error('\nOutputs are out of sync. Run `npm run build` and commit the results.');
  process.exit(1);
} else {
  console.log('Outputs are in sync.');
}
