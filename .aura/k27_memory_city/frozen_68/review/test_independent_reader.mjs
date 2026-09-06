import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const cli = fileURLToPath(new URL('../reader/kv-cache.mjs', import.meta.url));
test('existing --help CLI contract remains successful', () => {
  const result = spawnSync(process.execPath, [cli, '--help'], {encoding:'utf8'});
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /kv-cache\.mjs/);
});
