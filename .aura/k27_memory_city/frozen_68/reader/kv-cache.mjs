#!/usr/bin/env node
// Import-safe, read-only successor to the 2026-08-30 K27 reader.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const DEFAULT_STORE = path.join(process.env.USERPROFILE || process.env.HOME || '.', 'aura-drive-mirror', 'kv-cache', 'external-world-k27.json');
const V_KEYS = ['cell', 'digest', 'standing', 'reopen', 'successor'];
const DIGEST = /^[0-9a-f]{16}$/;
const KEY = /^(?:α0\/triad-3\/.+|external\/E-[A-Z]\d+\/arxiv:\d+\.\d+v\d+)$/u;
const indices = new WeakMap();
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;

export class KvError extends Error {
  constructor(type, message, extra = {}) { super(message); this.type = type; Object.assign(this, extra); }
}
function refuse(type, message, extra) { throw new KvError(type, message, extra); }
function freeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
function index(store) {
  if (indices.has(store)) return indices.get(store);
  if (!object(store) || !object(store.schema)) refuse('KV_ERR_UNPARSEABLE', 'store requires a schema object');
  if (store.schema.name !== 'aura-coordinate-memory-kv-v1' || store.schema.version !== '1.0.0')
    refuse('KV_ERR_SCHEMA_VERSION', 'unsupported store schema');
  if (!Array.isArray(store.rows)) refuse('KV_ERR_UNPARSEABLE', 'store requires rows array');
  const byK = new Map(), byDigest = new Map(), byCell = new Map();
  for (const [rowIndex, row] of store.rows.entries()) {
    if (!object(row) || !nonempty(row.K) || !object(row.V) || Object.keys(row.V).length !== 5 || !V_KEYS.every(k => nonempty(row.V[k])))
      refuse('KV_ERR_ROW_SHAPE', 'row requires K and five nonempty V fields', {rowIndex});
    if (!KEY.test(row.K)) refuse('KV_ERR_KEY_FORMAT', 'unsupported coordinate syntax', {rowIndex});
    if (!DIGEST.test(row.V.digest)) refuse('KV_ERR_DIGEST_FORMAT', 'digest requires 16 lowercase hexadecimal characters', {rowIndex});
    if (byK.has(row.K)) refuse('KV_ERR_DUPLICATE_KEY', 'coordinate has multiple rows', {key:row.K});
    byK.set(row.K, row);
    for (const [map, value] of [[byDigest, row.V.digest], [byCell, row.V.cell]]) {
      if (!map.has(value)) map.set(value, []);
      map.get(value).push(row);
    }
  }
  if (store.metadata?.row_count !== undefined && (!Number.isSafeInteger(store.metadata.row_count) || store.metadata.row_count !== store.rows.length))
    refuse('KV_ERR_ROW_COUNT', 'metadata.row_count differs from actual rows');
  freeze(store);
  const result = {byK, byDigest, byCell}; indices.set(store, result); return result;
}
export function parseStore(text, source = '<memory>') {
  let store;
  try { store = JSON.parse(text); }
  catch { refuse('KV_ERR_UNPARSEABLE', 'invalid JSON', {path:source}); }
  index(store); return store;
}
export function loadStore(storePath = DEFAULT_STORE) {
  let data;
  try { data = fs.readFileSync(storePath, 'utf8'); }
  catch (error) { refuse(error.code === 'ENOENT' ? 'KV_ERR_MISSING_FILE' : 'KV_ERR_READ_FILE', 'cannot read store', {path:storePath, code:error.code}); }
  return parseStore(data, storePath);
}
const hit = row => row ? ({K:row.K, V:row.V, standing:row.V.standing, reopen:row.V.reopen, successor:row.V.successor, lookupHintOnly:true}) : null;
export function byK(store, key) { return hit(index(store).byK.get(key)); }
export function byDigest(store, digest) {
  if (!DIGEST.test(digest)) refuse('KV_ERR_DIGEST_FORMAT', 'invalid lookup digest');
  const rows = index(store).byDigest.get(digest) || [];
  if (rows.length > 1) refuse('KV_ERR_AMBIGUOUS_DIGEST', 'short digest identifies multiple coordinates; use exact K', {digest, candidates:rows.map(r=>r.K).sort()});
  return hit(rows[0]);
}
export function byCell(store, cell) { return (index(store).byCell.get(cell) || []).map(hit).sort((a,b)=>a.K < b.K ? -1 : a.K > b.K ? 1 : 0); }
export function validateStore(store) {
  const ix = index(store);
  return {dataSound:true, rowCount:store.rows.length, uniqueKeys:ix.byK.size,
    ambiguousDigests:[...ix.byDigest.values()].filter(r=>r.length > 1).length,
    declaredCheckCount:Array.isArray(store.validation?.checks) ? store.validation.checks.length : null,
    declaredResult:store.validation?.result ?? null,
    declaredChecksExecuted:false,
    note:'Shape validation is executed here. Stored validation text is provenance, not proof that checks passed. Short digests are lookup hints, not content verification.'};
}
export function currentnessNote(storePath) {
  const resolved = path.resolve(storePath), mirror = path.dirname(path.resolve(DEFAULT_STORE));
  const relative = path.relative(mirror, resolved);
  const inMirror = relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
  return {storePath:resolved, inKnownMirror:inMirror, ambientSync:inMirror ? 'possible; recheck sync state before consequential reuse' : 'not established for this explicit path', readerWrites:false, note:'Recheck per-row reopen conditions; coordinates grant no authority.'};
}
export function selftest(store) {
  const ix = index(store), checks = [];
  checks.push({check:'every K round-trips', pass:store.rows.every(r=>byK(store,r.K)?.V === r.V)});
  checks.push({check:'every cell contains its row', pass:store.rows.every(r=>byCell(store,r.V.cell).some(h=>h.K === r.K))});
  checks.push({check:'every digest resolves uniquely or reports ambiguity', pass:[...ix.byDigest].every(([d, rows])=>{
    try { const found = byDigest(store,d); return rows.length === 1 && found?.K === rows[0].K; }
    catch (e) { return rows.length > 1 && e.type === 'KV_ERR_AMBIGUOUS_DIGEST'; }
  })});
  checks.push({check:'invalid schema rejected', pass:(()=>{try {parseStore('{"schema":{},"rows":[]}'); return false;} catch(e){return e.type==='KV_ERR_SCHEMA_VERSION';}})()});
  return {rowCount:store.rows.length, checks, passed:checks.filter(c=>c.pass).length, total:checks.length};
}
export function main(args = process.argv.slice(2)) {
  if (args.length === 1 && ['--help','-h','help'].includes(args[0])) {
    console.log('kv-cache.mjs OP [KEY] [STORE_PATH]\nOP: by-k, by-digest, by-cell, list, validate, selftest'); return 0;
  }
  const [op, ...rest] = args;
  const keyed = ['by-k','by-digest','by-cell'].includes(op);
  const expectedMax = keyed ? 2 : 1;
  if (!['by-k','by-digest','by-cell','list','validate','selftest'].includes(op) || rest.length > expectedMax || (keyed && !rest[0])) {
    console.error(JSON.stringify({type:'KV_USAGE', usage:'kv-cache.mjs OP [KEY] [STORE_PATH]'})); return 1;
  }
  const storePath = (keyed ? rest[1] : rest[0]) || DEFAULT_STORE;
  try {
    const store = loadStore(storePath), r1 = currentnessNote(storePath); let result;
    if (op === 'by-k') result = byK(store,rest[0]);
    if (op === 'by-digest') result = byDigest(store,rest[0]);
    if (op === 'by-cell') { const rows = byCell(store,rest[0]); result = rows.length ? {rows,count:rows.length} : null; }
    if (op === 'list') result = {rows:[...store.rows].sort((a,b)=>a.K < b.K ? -1 : a.K > b.K ? 1 : 0),total:store.rows.length};
    if (op === 'validate') result = validateStore(store);
    if (op === 'selftest') result = selftest(store);
    if (result === null) { console.log(JSON.stringify({type:'KV_MISS',op,key:rest[0]})); return 2; }
    console.log(JSON.stringify({op,...result,r1},null,2));
    return op === 'selftest' && result.passed !== result.total ? 4 : 0;
  } catch (error) {
    if (!(error instanceof KvError)) throw error;
    console.error(JSON.stringify({type:error.type,message:error.message,...error})); return 3;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) process.exitCode = main();
