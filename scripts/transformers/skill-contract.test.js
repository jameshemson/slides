import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { ROOT } from './utils.js';

// Contract gate for the authored skill prompts in source/skills/. Asserts:
//   - every source/skills/<skill>/SKILL.md carries `name` and `description`
//     frontmatter fields;
//   - prompt-size ceilings: presentation-craft/SKILL.md <= 210 lines, every
//     command (user-invocable) SKILL.md <= 170 lines, and each
//     presentation-craft/reference/*.md <= 190 lines.
//
// Vacuous-pass guard (finding I-003): if the glob finds ZERO SKILL.md files,
// this suite FAILS LOUDLY rather than passing silently — a missing source
// tree must never look like a green contract.

const SKILLS_DIR = join(ROOT, 'source', 'skills');

// Per-file hard line ceilings. Anything not listed here falls under the
// generic command-skill ceiling (COMMAND_SKILL_LINE_LIMIT).
const PRESENTATION_CRAFT_LINE_LIMIT = 210;
const COMMAND_SKILL_LINE_LIMIT = 170;
const REFERENCE_LINE_LIMIT = 190;

function lineCount(content) {
  return content.split('\n').length - (content.endsWith('\n') ? 1 : 0);
}

function parseFrontmatterFields(content, path) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n/);
  assert.ok(match, `${path} must begin with a YAML frontmatter block`);
  const fields = new Set();
  for (const line of match[1].split('\n')) {
    const m = line.match(/^([\w-]+):/);
    if (m) fields.add(m[1]);
  }
  return fields;
}

// Discover every source/skills/<skill>/SKILL.md.
function findSkillMds() {
  if (!existsSync(SKILLS_DIR)) return [];
  const out = [];
  for (const entry of readdirSync(SKILLS_DIR)) {
    const skillDir = join(SKILLS_DIR, entry);
    if (!statSync(skillDir).isDirectory()) continue;
    const skillMd = join(skillDir, 'SKILL.md');
    if (existsSync(skillMd) && statSync(skillMd).isFile()) {
      out.push({ skill: entry, path: skillMd });
    }
  }
  return out;
}

// Discover every presentation-craft/reference/*.md.
function findReferenceMds() {
  const refDir = join(SKILLS_DIR, 'presentation-craft', 'reference');
  if (!existsSync(refDir)) return [];
  return readdirSync(refDir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => ({ name: f, path: join(refDir, f) }));
}

const skillMds = findSkillMds();

test('source/skills contains at least one SKILL.md (vacuous-pass guard)', () => {
  assert.ok(
    skillMds.length > 0,
    `No SKILL.md files found under ${SKILLS_DIR}. The skill contract cannot ` +
      `pass vacuously — author the skills (Wave 2) before this gate can be green.`,
  );
});

test('every source/skills/*/SKILL.md has name and description frontmatter', () => {
  assert.ok(skillMds.length > 0, 'no SKILL.md files to check — see vacuous-pass guard');
  for (const { skill, path } of skillMds) {
    const fields = parseFrontmatterFields(readFileSync(path, 'utf8'), path);
    assert.ok(
      fields.has('name'),
      `${skill}/SKILL.md frontmatter must include a "name" field`,
    );
    assert.ok(
      fields.has('description'),
      `${skill}/SKILL.md frontmatter must include a "description" field`,
    );
  }
});

test('SKILL.md prompts stay below hard line ceilings', () => {
  assert.ok(skillMds.length > 0, 'no SKILL.md files to check — see vacuous-pass guard');
  for (const { skill, path } of skillMds) {
    const lines = lineCount(readFileSync(path, 'utf8'));
    const limit =
      skill === 'presentation-craft'
        ? PRESENTATION_CRAFT_LINE_LIMIT
        : COMMAND_SKILL_LINE_LIMIT;
    assert.ok(
      lines <= limit,
      `${skill}/SKILL.md has ${lines} lines, exceeding hard ceiling ${limit}`,
    );
  }
});

test('presentation-craft reference files stay below hard line ceiling', () => {
  for (const { name, path } of findReferenceMds()) {
    const lines = lineCount(readFileSync(path, 'utf8'));
    assert.ok(
      lines <= REFERENCE_LINE_LIMIT,
      `presentation-craft/reference/${name} has ${lines} lines, exceeding hard ceiling ${REFERENCE_LINE_LIMIT}`,
    );
  }
});
