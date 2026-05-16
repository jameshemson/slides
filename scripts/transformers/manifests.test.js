import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, statSync, readdirSync } from 'fs';
import { join } from 'path';
import { ROOT } from './utils.js';
import { VERSION_CARRIERS } from './version-carriers.js';

const codexPluginPath = join(ROOT, 'plugins/slides/.codex-plugin/plugin.json');
const marketplacePath = join(ROOT, '.agents/plugins/marketplace.json');
const codexSkillsDir = join(ROOT, 'plugins/slides/skills');
const codexCrossSkillsDir = join(ROOT, '.codex/skills');
const opencodeCommandsDir = join(ROOT, '.opencode/commands');
const sourceCommandsDir = join(ROOT, 'source/commands');
const sourceSkillsDir = join(ROOT, 'source/skills');

// All five slides skills are portable — no provider excludes any of them.
const PORTABLE_SKILLS = [
  'build-deck',
  'narrative',
  'presentation-craft',
  'slop-check',
  'teach-slides',
];

// The four user-invocable skills have OpenCode command wrappers;
// presentation-craft is a non-invocable knowledge base and has none.
const COMMAND_SKILLS = ['build-deck', 'narrative', 'slop-check', 'teach-slides'];

function readDescription(mdPath) {
  const content = readFileSync(mdPath, 'utf8');
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) throw new Error(`No frontmatter in ${mdPath}`);
  const line = match[1].split('\n').find((l) => l.startsWith('description:'));
  if (!line) throw new Error(`No description in ${mdPath}`);
  return line.slice('description:'.length).trim();
}

// Known-good Codex manifest enum values, verified against
// https://developers.openai.com/codex/plugins/build on 2026-04-22.
// If Codex changes these enums, update here and re-run manual install test.
const VALID_SOURCE_TYPES = new Set(['local', 'url', 'git-subdir']);
const VALID_INSTALLATION_POLICIES = new Set([
  'AVAILABLE',
  'INSTALLED_BY_DEFAULT',
  'NOT_AVAILABLE',
]);
const VALID_AUTHENTICATION_POLICIES = new Set(['ON_INSTALL']);

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

test('Codex plugin.json parses and has required fields', () => {
  const plugin = readJson(codexPluginPath);
  assert.equal(plugin.name, 'slides');
  assert.match(plugin.version, /^\d+\.\d+\.\d+$/);
  assert.equal(typeof plugin.description, 'string');
  assert.ok(plugin.description.length > 0);
  assert.equal(plugin.skills, './skills/');
});

test('all release-version carriers agree', () => {
  const carriers = VERSION_CARRIERS.map((c) => ({
    path: c.path,
    version: c.get(readJson(join(ROOT, c.path))),
  }));
  const unique = [...new Set(carriers.map((c) => c.version))];
  assert.equal(
    unique.length,
    1,
    `Version drift across release files: ${carriers.map((c) => `${c.path}=${c.version}`).join(', ')}. Bump all ${carriers.length} together.`,
  );
});

test('Codex marketplace.json parses', () => {
  const market = readJson(marketplacePath);
  assert.equal(typeof market, 'object');
  assert.ok(market !== null);
});

test('Codex marketplace.json lists the slides plugin with expected source shape', () => {
  const market = readJson(marketplacePath);
  assert.equal(market.plugins.length, 1);
  const entry = market.plugins[0];
  assert.equal(entry.name, 'slides');
  assert.equal(entry.source.source, 'local');
  assert.equal(entry.source.path, './plugins/slides');
});

test('Codex marketplace plugin name matches plugin.json name', () => {
  const market = readJson(marketplacePath);
  const plugin = readJson(codexPluginPath);
  assert.equal(market.plugins[0].name, plugin.name);
});

test('plugins/slides/skills directory exists', () => {
  assert.ok(statSync(codexSkillsDir).isDirectory());
});

test('plugins/slides/skills contains exactly the five portable skills', () => {
  const entries = readdirSync(codexSkillsDir).sort();
  assert.deepEqual(entries, PORTABLE_SKILLS);
});

test('Codex marketplace source.source is a known Codex-recognised value', () => {
  const market = readJson(marketplacePath);
  const value = market.plugins[0].source.source;
  assert.ok(
    VALID_SOURCE_TYPES.has(value),
    `source.source="${value}" is not in Codex enum {${[...VALID_SOURCE_TYPES].join(', ')}}`,
  );
});

test('Codex marketplace policy.installation is a known Codex-recognised value', () => {
  const market = readJson(marketplacePath);
  const value = market.plugins[0].policy.installation;
  assert.ok(
    VALID_INSTALLATION_POLICIES.has(value),
    `policy.installation="${value}" is not in Codex enum {${[...VALID_INSTALLATION_POLICIES].join(', ')}}`,
  );
});

test('Codex marketplace policy.authentication is a known Codex-recognised value', () => {
  const market = readJson(marketplacePath);
  const value = market.plugins[0].policy.authentication;
  assert.ok(
    VALID_AUTHENTICATION_POLICIES.has(value),
    `policy.authentication="${value}" is not in Codex enum {${[...VALID_AUTHENTICATION_POLICIES].join(', ')}}`,
  );
});

test('Codex marketplace category is a non-empty string', () => {
  const market = readJson(marketplacePath);
  // Codex docs treat category as a free string; assert it's set.
  assert.equal(typeof market.plugins[0].category, 'string');
  assert.ok(market.plugins[0].category.length > 0);
});

test('.codex/skills/ contains exactly the five portable skills', () => {
  const entries = readdirSync(codexCrossSkillsDir).sort();
  assert.deepEqual(entries, PORTABLE_SKILLS);
});

test('.opencode/commands/ contains exactly the four expected command files', () => {
  const entries = readdirSync(opencodeCommandsDir).sort();
  assert.deepEqual(
    entries,
    COMMAND_SKILLS.map((n) => `${n}.md`),
  );
});

test('each source/commands/*.md description matches the corresponding source/skills/<name>/SKILL.md description', () => {
  // Command descriptions are maintained by hand; this test locks in
  // skill/command description parity so the OpenCode TUI shows the same
  // description as the skill's own SKILL.md frontmatter.
  for (const name of COMMAND_SKILLS) {
    const cmd = readDescription(join(sourceCommandsDir, `${name}.md`));
    const skill = readDescription(join(sourceSkillsDir, name, 'SKILL.md'));
    assert.equal(
      cmd,
      skill,
      `description mismatch for ${name}: command="${cmd}" skill="${skill}"`,
    );
  }
});

test('source/commands/ name set matches the user-invocable skill name set', () => {
  // Parity gate: if a contributor renames a user-invocable skill but forgets
  // to rename its command wrapper, this test fires. presentation-craft is a
  // non-invocable knowledge base and is excluded from the command set.
  const skillNames = readdirSync(sourceSkillsDir)
    .filter((n) => !['presentation-craft'].includes(n))
    .sort();
  const commandNames = readdirSync(sourceCommandsDir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => f.replace(/\.md$/, ''))
    .sort();
  assert.deepEqual(
    commandNames,
    skillNames,
    'source/commands/ must have one .md file per user-invocable skill (presentation-craft is non-invocable and excluded)',
  );
});
