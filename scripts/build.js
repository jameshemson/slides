import { join } from 'path';
import { ROOT } from './transformers/utils.js';
import { PROVIDERS, COMMAND_PROVIDERS } from './transformers/providers.js';
import { build, buildCommands } from './transformers/builder.js';

const SKILLS_SOURCE_DIR = join(ROOT, 'source', 'skills');
const COMMANDS_SOURCE_DIR = join(ROOT, 'source', 'commands');

console.log('Building...');
build({ root: ROOT, sourceDir: SKILLS_SOURCE_DIR, providers: PROVIDERS });
for (const [name, config] of Object.entries(PROVIDERS)) {
  console.log(`  ${name} → ${config.outputDir}`);
}
buildCommands({ root: ROOT, sourceDir: COMMANDS_SOURCE_DIR, providers: COMMAND_PROVIDERS });
for (const [name, config] of Object.entries(COMMAND_PROVIDERS)) {
  console.log(`  ${name} commands → ${config.outputDir}`);
}
console.log('Done.');
