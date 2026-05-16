import { test } from 'node:test';
import assert from 'node:assert/strict';
import { transform } from './transform.js';
import { PROVIDERS } from './providers.js';
import { parseFrontmatter, filterFrontmatter } from './frontmatter.js';
import { applyBodyRewrites } from './body-rewrites.js';

const SAMPLE = `---
name: build-deck
description: A thing.
user-invocable: true
argument-hint: "[what to build]"
model: opus
effort: high
context: fork
allowed-tools:
  - Bash(*)
---

Do something with /slides:narrative and then /slides:slop-check.

Consider $ARGUMENTS when planning.

$ARGUMENTS
`;

test('claude: identity transform (content unchanged)', () => {
  const out = transform(SAMPLE, 'claude', PROVIDERS.claude);
  assert.equal(out, SAMPLE);
});

test('opencode: strips Claude-only frontmatter fields', () => {
  const out = transform(SAMPLE, 'opencode', PROVIDERS.opencode);
  assert.match(out, /^---\nname: build-deck\ndescription: A thing\.\n---\n/);
  assert.doesNotMatch(out, /user-invocable/);
  assert.doesNotMatch(out, /argument-hint/);
  assert.doesNotMatch(out, /^model:/m);
  assert.doesNotMatch(out, /^effort:/m);
  assert.doesNotMatch(out, /^context:/m);
  assert.doesNotMatch(out, /allowed-tools/);
  assert.doesNotMatch(out, /Bash\(\*\)/);
});

test('codex: strips Claude-only frontmatter fields', () => {
  const out = transform(SAMPLE, 'codex', PROVIDERS.codex);
  assert.match(out, /^---\nname: build-deck\ndescription: A thing\.\n---\n/);
  assert.doesNotMatch(out, /allowed-tools/);
});

test('opencode: rewrites $ARGUMENTS (standalone and inline)', () => {
  const out = transform(SAMPLE, 'opencode', PROVIDERS.opencode);
  assert.doesNotMatch(out, /\$ARGUMENTS/);
  // Standalone line replaced with italic prose block
  assert.match(out, /\*\(Treat the user's message.*?task input\.\)\*/);
  // Inline occurrence replaced with "the user's request"
  assert.match(out, /Consider the user's request when planning/);
});

test('opencode: skillRef produces OpenCode-specific phrasing', () => {
  const out = transform(SAMPLE, 'opencode', PROVIDERS.opencode);
  assert.doesNotMatch(out, /\/slides:/);
  assert.match(out, /`narrative` \(via the skill tool\)/);
  assert.match(out, /`slop-check` \(via the skill tool\)/);
});

test('codex: skillRef produces Codex-specific phrasing distinct from OpenCode', () => {
  const codexOut = transform(SAMPLE, 'codex', PROVIDERS.codex);
  const opencodeOut = transform(SAMPLE, 'opencode', PROVIDERS.opencode);
  assert.doesNotMatch(codexOut, /\/slides:/);
  assert.match(codexOut, /`narrative` \(via `\$skill narrative` or `\/skills`\)/);
  assert.match(codexOut, /`slop-check` \(via `\$skill slop-check` or `\/skills`\)/);
  // And the two providers emit different text for the same source
  assert.notEqual(codexOut, opencodeOut);
});

test('filterFrontmatter handles multi-line block sequences', () => {
  const raw = `name: x
allowed-tools:
  - Bash(*)
  - Read
description: keep this`;
  const filtered = filterFrontmatter(raw, 'opencode');
  assert.equal(filtered, 'name: x\ndescription: keep this');
});

test('parseFrontmatter returns body unchanged when no frontmatter', () => {
  const plain = 'Just a paragraph.\nNo frontmatter here.\n';
  const { rawFm, body } = parseFrontmatter(plain);
  assert.equal(rawFm, null);
  assert.equal(body, plain);
});

test('body rewrites: null rewrites (Claude) is identity', () => {
  const body = 'call /slides:build-deck and $ARGUMENTS.';
  assert.equal(applyBodyRewrites(body, null), body);
});

test('body rewrites: removes claude-only HTML comment blocks', () => {
  const body = 'before\n<!-- claude-only -->\nclaude internals\n<!-- /claude-only -->\nafter';
  const out = applyBodyRewrites(body, PROVIDERS.opencode.rewrites);
  assert.doesNotMatch(out, /claude internals/);
  assert.match(out, /before/);
  assert.match(out, /after/);
});

test('transform is idempotent on its own output for Claude', () => {
  const once = transform(SAMPLE, 'claude', PROVIDERS.claude);
  const twice = transform(once, 'claude', PROVIDERS.claude);
  assert.equal(once, twice);
});
