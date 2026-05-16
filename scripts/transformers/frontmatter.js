// Supported frontmatter grammar (subset of YAML):
//   - Top-level keys are `^[\w-]+:` at column 0.
//   - Values are either inline scalars or indented block sequences (`  - item`).
//   - Indented continuations (any line starting with a space or tab) inherit
//     the skip state of their parent key. Block scalars (`key: |`) are not
//     supported — treat them as a future extension if needed.
// Fields that only Claude Code understands — stripped from non-Claude outputs.
const CLAUDE_ONLY_FIELDS = new Set([
  'user-invocable',
  'argument-hint',
  'model',
  'effort',
  'context',
  'allowed-tools',
]);

/**
 * Split a SKILL.md string into its raw frontmatter text and body.
 * Returns { rawFm: string|null, body: string }.
 */
export function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { rawFm: null, body: content };
  return { rawFm: match[1], body: match[2] };
}

/**
 * Filter Claude-only fields from a raw frontmatter string.
 * Handles both single-line and multi-line (indented list) values.
 * For provider === 'claude', returns input unchanged.
 */
export function filterFrontmatter(rawFm, provider) {
  if (provider === 'claude') return rawFm;

  const lines = rawFm.split('\n');
  const kept = [];
  let skip = false;

  for (const line of lines) {
    const topLevel = line.match(/^([\w-]+):/);
    if (topLevel) {
      skip = CLAUDE_ONLY_FIELDS.has(topLevel[1]);
    } else if (/^[ \t]/.test(line)) {
      // indented continuation — inherit parent skip state
    } else {
      // blank or other line resets skip
      skip = false;
    }
    if (!skip) kept.push(line);
  }

  return kept.join('\n');
}
