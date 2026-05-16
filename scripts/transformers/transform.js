import { parseFrontmatter, filterFrontmatter } from './frontmatter.js';
import { applyBodyRewrites } from './body-rewrites.js';

/**
 * Transform a SKILL.md string for a given provider.
 * Returns the full transformed file content.
 */
export function transform(content, provider, providerConfig) {
  const { rawFm, body } = parseFrontmatter(content);

  const rewrittenBody = applyBodyRewrites(body, providerConfig.rewrites);

  if (rawFm === null) {
    return rewrittenBody;
  }

  const filteredFm = filterFrontmatter(rawFm, provider);
  return `---\n${filteredFm}\n---\n${rewrittenBody}`;
}
