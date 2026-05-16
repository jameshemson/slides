/**
 * Apply body rewrites for non-Claude harnesses.
 * rewrites === null means identity (Claude target).
 */
export function applyBodyRewrites(body, rewrites) {
  if (!rewrites) return body;

  let out = body;

  // 1. Standalone $ARGUMENTS: a line containing only $ARGUMENTS (with optional whitespace).
  //    These are the "inject user input here" markers.
  out = out.replace(
    /^[ \t]*\$ARGUMENTS[ \t]*$/gm,
    rewrites.argumentsStandalone,
  );

  // 2. Inline $ARGUMENTS remaining in prose (e.g. "requirements in $ARGUMENTS").
  out = out.replace(/\$ARGUMENTS/g, rewrites.argumentsInline);

  // 3. /slides:<name> slash-command references.
  out = out.replace(/\/slides:([\w-]+)/g, (_, name) => rewrites.skillRef(name));

  // 4. <!-- claude-only --> ... <!-- /claude-only --> blocks.
  out = out.replace(/<!-- claude-only -->[\s\S]*?<!-- \/claude-only -->/g, '');

  return out;
}
