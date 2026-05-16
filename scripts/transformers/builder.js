import {
  readdirSync,
  statSync,
  mkdirSync,
  copyFileSync,
  existsSync,
  unlinkSync,
  readFileSync,
  writeFileSync,
} from 'fs';
import { join, dirname } from 'path';
import { transform } from './transform.js';

function walkFiles(root, dir, callback) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walkFiles(root, full, callback);
    } else {
      callback(full, full.slice(root.length + 1));
    }
  }
}

function listAllFiles(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  walkFiles(dir, dir, (fullPath) => out.push(fullPath));
  return out;
}

function writeFile(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, 'utf8');
}

/**
 * Emit one provider's output from sourceDir.
 *
 * Cleanup strategy: we never remove directories — live harnesses (Codex,
 * editors) may hold watchers on output dirs and recursive rm triggers EPERM.
 * Instead we track every file we write this run, then unlink any pre-existing
 * file in the output tree that was not part of the emit set. Directories stay
 * in place; an empty leftover directory is harmless.
 */
export function buildProvider({ root, sourceDir, providerName, config }) {
  const outBase = join(root, config.outputDir);
  mkdirSync(outBase, { recursive: true });

  const emitted = new Set();

  for (const skillName of readdirSync(sourceDir)) {
    const skillDir = join(sourceDir, skillName);
    if (!statSync(skillDir).isDirectory()) continue;
    if (config.exclude.includes(skillName)) continue;

    walkFiles(skillDir, skillDir, (filePath, relPath) => {
      const outPath = join(outBase, skillName, relPath);
      emitted.add(outPath);

      if (relPath.endsWith('.md')) {
        const content = readFileSync(filePath, 'utf8');
        writeFile(outPath, transform(content, providerName, config));
      } else {
        mkdirSync(dirname(outPath), { recursive: true });
        copyFileSync(filePath, outPath);
      }
    });
  }

  // File-only sweep: remove any file in outBase not emitted this run.
  for (const existing of listAllFiles(outBase)) {
    if (!emitted.has(existing)) {
      unlinkSync(existing);
    }
  }
}

export function buildCommandProvider({ root, sourceDir, providerName, config }) {
  const outBase = join(root, config.outputDir);
  mkdirSync(outBase, { recursive: true });

  const emitted = new Set();

  for (const entry of readdirSync(sourceDir)) {
    const sourcePath = join(sourceDir, entry);
    if (!statSync(sourcePath).isFile()) continue;
    if (!entry.endsWith('.md')) continue;

    const outPath = join(outBase, entry);
    emitted.add(outPath);

    const content = readFileSync(sourcePath, 'utf8');
    writeFile(outPath, transform(content, providerName, config));
  }

  for (const existing of listAllFiles(outBase)) {
    if (!emitted.has(existing)) {
      unlinkSync(existing);
    }
  }
}

export function build({ root, sourceDir, providers }) {
  for (const [name, config] of Object.entries(providers)) {
    buildProvider({ root, sourceDir, providerName: name, config });
  }
}

export function buildCommands({ root, sourceDir, providers }) {
  for (const [name, config] of Object.entries(providers)) {
    buildCommandProvider({ root, sourceDir, providerName: name, config });
  }
}
