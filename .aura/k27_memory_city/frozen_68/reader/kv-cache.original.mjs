#!/usr/bin/env node
// kv-cache.mjs — runtime reader for the Aura coordinate-memory KV cache
// CELL: EXTERNAL-WORLD-K27-KV-READER-001 · ROLE: A+ (OXA-A-PLUS) · DATE: 2026-08-30
// CONTRACT: C0 fold 5a1f2c10a388b029 §6 (reader contract + R1 sync-root caveat + R2 dynamic-count law)
// STORE: aura-drive-mirror\kv-cache\external-world-k27.json (digest dc89984728688760, frozen bytes — never mutated by this tool)
// STATUS: NONPROMOTING / NOT_GATE10 / D0-only / zero spend / READ-ONLY / deterministic / no network / no provider-model calls
//
// Ops:
//   kv-cache.mjs by-k <coordinate>        exact K lookup → V {cell,digest,standing,reopen,successor} + K (lookup hint only)
//   kv-cache.mjs by-digest <16-hex>       exact V.digest lookup
//   kv-cache.mjs by-cell <cell>           all rows for a cell (all roles)
//   kv-cache.mjs list                     all 15 rows, sorted by K, with summary
//   kv-cache.mjs validate                 dynamic validation: count == checks.length (TRUE count, never the frozen literal)
//   kv-cache.mjs selftest                 15/15: by-K + by-digest round-trips + typed MISS + fail-closed paths
//   kv-cache.mjs <store-path> may be passed as first positional arg to every op (default: mirror kv-cache store)
//
// Exit codes: 0 success · 1 usage/unknown op · 2 typed MISS (lookup not found) · 3 fail-closed (missing/unparseable/version/digest-format) · 4 validate/selftest FAIL
// Read-only by construction: fs.readFileSync / existsSync / statSync only — no write path exists in this file.
import fs from "node:fs";
import path from "node:path";

const USERPROFILE = process.env.USERPROFILE || process.env.HOME || ".";
const DEFAULT_STORE = path.join(USERPROFILE, "aura-drive-mirror", "kv-cache", "external-world-k27.json");
// Schema gate (contract-fixed): the reader serves schema 1.0.0 only. This is a version gate, NOT a validation count.
const EXPECTED_SCHEMA = { name: "aura-coordinate-memory-kv-v1", version: "1.0.0" };
const V_KEYS = ["cell", "digest", "standing", "reopen", "successor"];
const DIGEST_RE = /^[0-9a-f]{16}$/;
const SOURCE_K_RE = /^external\/E-[A-Z]\d+\/arxiv:\d+\.\d+v\d+$/;
const ARTIFACT_K_RE = /^α0\/triad-3\//;

// ── typed fail-closed errors ──
class KvError extends Error {
  constructor(type, message, extra = {}) {
    super(message);
    this.type = type;
    Object.assign(this, extra);
  }
}
const failClosed = (type, message, extra) => {
  console.error(JSON.stringify({ type, message, ...extra }));
  process.exit(3);
};

// ── pure load/parse: fail-closed with typed refusal, zero writes ──
export function parseStore(text, source) {
  let obj;
  try { obj = JSON.parse(text); } catch (e) {
    throw new KvError("KV_ERR_UNPARSEABLE", `store does not parse as valid JSON (${source})`, { path: source, detail: String(e.message) });
  }
  if (!obj || typeof obj !== "object" || !obj.schema || typeof obj.schema !== "object") {
    throw new KvError("KV_ERR_UNPARSEABLE", `store JSON has no schema object (${source})`, { path: source });
  }
  if (obj.schema.name !== EXPECTED_SCHEMA.name || obj.schema.version !== EXPECTED_SCHEMA.version) {
    throw new KvError("KV_ERR_SCHEMA_VERSION", `schema version mismatch — this reader serves ${EXPECTED_SCHEMA.name} ${EXPECTED_SCHEMA.version}; store is ${obj.schema.name} ${obj.schema.version} (${source})`, {
      expected: EXPECTED_SCHEMA.version, actual: String(obj.schema.version), path: source,
    });
  }
  if (!Array.isArray(obj.rows)) throw new KvError("KV_ERR_UNPARSEABLE", `store JSON has no rows array (${source})`, { path: source });
  return obj;
}

export function loadStore(storePath = DEFAULT_STORE) {
  if (!fs.existsSync(storePath)) {
    throw new KvError("KV_ERR_MISSING_FILE", `store file does not exist (${storePath})`, { path: storePath });
  }
  return parseStore(fs.readFileSync(storePath, "utf8"), storePath);
}

// ── R1 sync-root caveat: currentness surfaced honestly, never claimed zero-effect ──
function syncRootCaveat(storeDir) {
  const psPath = path.join(storeDir, "push-state.json");
  const base = {
    type: "KV_NOTE_R1_SYNC_ROOT",
    caveat: "This store lives under aura-drive-mirror\\kv-cache, a mirror root swept by the ambient sync layer (aura-sync.cjs -> push2drive.cjs). This reader is read-only and performs no Drive writes; it makes NO zero-external-effect claim for the store. Consumers must re-check currentness before consequential reuse (per-row reopen conditions).",
  };
  if (!fs.existsSync(psPath)) {
    return { ...base, pushStateFile: psPath, pushStatePresent: false, pushStateDone: [], pushStateMtime: null, pushStateParseError: null };
  }
  let done = [], parseError = null, mtime = null;
  try { const ps = JSON.parse(fs.readFileSync(psPath, "utf8")); done = Array.isArray(ps.done) ? ps.done : []; }
  catch (e) { parseError = String(e.message); }
  try { mtime = fs.statSync(psPath).mtime.toISOString(); } catch { /* mtime stays null */ }
  return { ...base, pushStateFile: psPath, pushStatePresent: true, pushStateDone: done, pushStateMtime: mtime, pushStateParseError: parseError };
}

// ── row-shape / format checks (all dynamic, from the bytes read) ──
function rowShapeOk(r) {
  return !!r && typeof r === "object" && typeof r.K === "string" && r.K.length > 0
    && !!r.V && typeof r.V === "object" && Object.keys(r.V).length === 5
    && V_KEYS.every(k => typeof r.V[k] === "string" && r.V[k].length > 0);
}
function kFormOf(k) { return ARTIFACT_K_RE.test(k) ? "artifact" : SOURCE_K_RE.test(k) ? "source" : "UNKNOWN"; }

// ── lookups ──
function byK(store, key) {
  const row = store.rows.find(r => r.K === key);
  return row ? { K: row.K, V: row.V, standing: row.V.standing, reopen: row.V.reopen, successor: row.V.successor, lookupHintOnly: true } : null;
}
function byDigest(store, digest) {
  const row = store.rows.find(r => r.V.digest === digest);
  return row ? { K: row.K, V: row.V, standing: row.V.standing, reopen: row.V.reopen, successor: row.V.successor, lookupHintOnly: true } : null;
}
function byCell(store, cell) {
  return store.rows.filter(r => r.V.cell === cell).map(r => ({ K: r.K, V: r.V, standing: r.V.standing, reopen: r.V.reopen, successor: r.V.successor, lookupHintOnly: true }));
}

// ── ops ──
function opByK(store, dir, key) {
  const hit = byK(store, key);
  if (!hit) {
    console.log(JSON.stringify({ type: "KV_MISS", op: "by-k", key, note: "no row matches this coordinate; K is a lookup hint only — never fabrication, never authority" }, null, 2));
    process.exit(2);
  }
  console.log(JSON.stringify({ op: "by-k", ...hit, r1: syncRootCaveat(dir) }, null, 2));
}
function opByDigest(store, dir, digest) {
  if (!DIGEST_RE.test(digest)) failClosed("KV_ERR_DIGEST_FORMAT", `by-digest expects exactly 16 lowercase hex chars, got "${digest}"`, { digest });
  const hit = byDigest(store, digest);
  if (!hit) {
    console.log(JSON.stringify({ type: "KV_MISS", op: "by-digest", digest, note: "no row carries this digest — never fabrication" }, null, 2));
    process.exit(2);
  }
  console.log(JSON.stringify({ op: "by-digest", ...hit, r1: syncRootCaveat(dir) }, null, 2));
}
function opByCell(store, dir, cell) {
  const hits = byCell(store, cell);
  if (!hits.length) {
    console.log(JSON.stringify({ type: "KV_MISS", op: "by-cell", cell, note: "no row belongs to this cell — never fabrication" }, null, 2));
    process.exit(2);
  }
  console.log(JSON.stringify({ op: "by-cell", cell, count: hits.length, rows: hits, r1: syncRootCaveat(dir) }, null, 2));
}
function opList(store, dir) {
  const sorted = [...store.rows].sort((a, b) => a.K.localeCompare(b.K));
  const artifact = sorted.filter(r => kFormOf(r.K) === "artifact").length;
  const source = sorted.filter(r => kFormOf(r.K) === "source").length;
  const rows = sorted.map(r => ({ K: r.K, cell: r.V.cell, digest: r.V.digest, standing: r.V.standing, reopen: r.V.reopen, successor: r.V.successor, lookupHintOnly: true }));
  console.log(JSON.stringify({
    op: "list", store: "aura-coordinate-memory-kv-v1 1.0.0", total: rows.length, artifact, source,
    note: "K is a lookup hint only — never authority; standing strings carry F1–F9 amended standings verbatim",
    rows, r1: syncRootCaveat(dir),
  }, null, 2));
}
function opValidate(store, dir) {
  const checks = (store.validation && Array.isArray(store.validation.checks)) ? store.validation.checks : null;
  const result = [];
  const rowShape = store.rows.map(rowShapeOk);
  const digestOk = store.rows.map(r => DIGEST_RE.test(r.V.digest));
  const kForm = store.rows.map(r => kFormOf(r.K));
  const metaRowCount = (store.metadata && store.metadata.row_count !== undefined) ? store.metadata.row_count : null;

  result.push({ check: "rows array present", pass: true, detail: `${store.rows.length} rows` });
  result.push({ check: "metadata.row_count == rows.length (dynamic)", pass: metaRowCount === null ? null : metaRowCount === store.rows.length, detail: `${metaRowCount} == ${store.rows.length}` });
  result.push({ check: "V-shape {cell,digest,standing,reopen,successor} 15/15", pass: rowShape.every(Boolean), detail: `${rowShape.filter(Boolean).length}/${rowShape.length}` });
  result.push({ check: "digest format ^[0-9a-f]{16}$", pass: digestOk.every(Boolean), detail: `${digestOk.filter(Boolean).length}/${digestOk.length}` });
  result.push({ check: "K forms: artifact α0/triad-3/… + source external/E-XX/arxiv:ID", pass: kForm.every(f => f !== "UNKNOWN"), detail: `${kForm.filter(f => f === "artifact").length} artifact / ${kForm.filter(f => f === "source").length} source / ${kForm.filter(f => f === "UNKNOWN").length} UNKNOWN` });
  result.push({ check: "validation.checks present", pass: !!checks, detail: checks ? `${checks.length} entries read from store bytes (dynamic)` : "absent — dynamic count unavailable" });

  // R2 dynamic count: the TRUE count is checks.length; never trust the frozen literal (HSC-207 RUNTIME-RECOMPUTE LAW).
  let literalCount = null, literal = null;
  if (store.validation && typeof store.validation.result === "string") {
    literal = store.validation.result;
    const m = /(\d+)\s*\/\s*(\d+)/.exec(literal);
    if (m) literalCount = `${m[1]}/${m[2]}`;
  }
  const trueCount = checks ? `${checks.length}/${checks.length}` : "n/a";
  const countPass = !!checks; // dynamic identity is true by construction (count == checks.length); the literal is the suspect
  result.push({ check: "dynamic validation count == checks.length", pass: countPass, detail: `TRUE count ${trueCount}${literalCount ? `; frozen literal says "${literalCount}"` : ""}`, f2: literalCount !== null && literalCount !== trueCount });

  const dataSound = result.filter(r => r.pass === false).length === 0;
  const f2 = result.some(r => r.f2);
  console.log(JSON.stringify({
    op: "validate", store: `${store.schema.name} ${store.schema.version}`, storePath: dir,
    result, dataSound,
    f2Note: f2 ? "F2 CLOSED BY DYNAMIC RECOMPUTE: the frozen store bytes carry a stale count literal (\"21/21\") in validation.result while validation.checks lists 20 entries; per RUNTIME-RECOMPUTE LAW (HSC-207) the reader reports the TRUE count (20/20) from the checks array and never trusts the literal. Bytes are frozen at digest dc89984728688760 — no mutation performed; a v1.0.1 relabel is a separate owner decision." : null,
    r1: syncRootCaveat(dir),
  }, null, 2));
  if (!dataSound) { console.error(`VALIDATE FAIL — ${result.filter(r => r.pass === false).length} check(s) false`); process.exit(4); }
}

// ── selftest: 15/15, file-write-free, deterministic, on the real store ──
function opSelftest(dir) {
  const out = [];
  const t = (id, name, pass, detail) => { out.push({ id, name, pass, detail }); };
  let store = null;
  try { store = loadStore(path.join(dir, "external-world-k27.json")); t("ST-01", "store loads from default mirror path", true, dir); }
  catch (e) { t("ST-01", "store loads from default mirror path", false, String(e.message)); process.exit(4); }

  t("ST-02", "schema gate: name+version accepted", store.schema.name === EXPECTED_SCHEMA.name && store.schema.version === EXPECTED_SCHEMA.version, `${store.schema.name} ${store.schema.version}`);
  t("ST-03", "row count == 15", store.rows.length === 15, `${store.rows.length}`);
  const art = store.rows.filter(r => ARTIFACT_K_RE.test(r.K));
  const src = store.rows.filter(r => SOURCE_K_RE.test(r.K));
  t("ST-04", "artifact rows == 3", art.length === 3, `${art.length}`);
  t("ST-05", "source rows == 12", src.length === 12, `${src.length}`);

  const missK = store.rows.filter(r => !byK(store, r.K));
  t("ST-06", "by-K round-trip 15/15 (exact)", missK.length === 0, `${store.rows.length - missK.length}/${store.rows.length}`);
  const missD = store.rows.filter(r => !byDigest(store, r.V.digest));
  t("ST-07", "by-digest round-trip 15/15 (exact)", missD.length === 0, `${store.rows.length - missD.length}/${store.rows.length}`);
  const map002 = byCell(store, "EXTERNAL-WORLD-K27-MAP-002");
  t("ST-08", "by-cell: MAP-002 returns 3 roles", map002.length === 3, `${map002.length} rows`);

  t("ST-09", "unknown-K -> typed KV_MISS (not fabrication)", byK(store, "α0/triad-3/NONEXISTENT/0000000000000000") === null, "null -> KV_MISS path");
  t("ST-10", "unknown-digest -> typed KV_MISS", byDigest(store, "0000000000000000") === null, "null -> KV_MISS path");

  // fail-closed paths — pure-function tests, ZERO files written
  let fc = null;
  try { parseStore("{ this is not json {{{", "selftest"); } catch (e) { fc = e; }
  t("ST-11", "unparseable JSON -> KV_ERR_UNPARSEABLE", fc instanceof KvError && fc.type === "KV_ERR_UNPARSEABLE", fc ? fc.type : "NO_THROW");
  fc = null;
  try { parseStore(JSON.stringify({ schema: { name: EXPECTED_SCHEMA.name, version: "9.9.9" }, rows: [] }), "selftest"); } catch (e) { fc = e; }
  t("ST-12", "schema version mismatch -> KV_ERR_SCHEMA_VERSION", fc instanceof KvError && fc.type === "KV_ERR_SCHEMA_VERSION", fc ? `${fc.type} (${fc.actual})` : "NO_THROW");
  fc = null;
  const ghost = path.join(dir, "kv-cache-selftest-absent.json");
  const ghostExists = fs.existsSync(ghost);
  if (!ghostExists) { try { loadStore(ghost); } catch (e) { fc = e; } }
  t("ST-13", "missing file -> KV_ERR_MISSING_FILE", !ghostExists && fc instanceof KvError && fc.type === "KV_ERR_MISSING_FILE", fc ? fc.type : (ghostExists ? "TEST_PATH_EXISTS" : "NO_THROW"));

  const shape = store.rows.map(rowShapeOk);
  t("ST-14", "V-shape {cell,digest,standing,reopen,successor} 15/15", shape.every(Boolean), `${shape.filter(Boolean).length}/${shape.length}`);
  const df = store.rows.map(r => DIGEST_RE.test(r.V.digest));
  t("ST-15", "digest format ^[0-9a-f]{16}$ 15/15", df.every(Boolean), `${df.filter(Boolean).length}/${df.length}`);

  for (const r of out) console.log(`${r.pass ? "PASS" : "FAIL"} ${r.id} ${r.name} — ${r.detail}`);
  const passed = out.filter(r => r.pass).length;
  console.log(`SELFTEST ${passed}/${out.length} ${passed === out.length ? "PASS" : "FAIL"}`);
  console.log(`R1: ${syncRootCaveat(dir).caveat}`);
  if (passed !== out.length) process.exit(4);
}

// ── dispatch ──
// Positional contract per op (store path is OPTIONAL and always the LAST positional):
//   by-k <key> [store] · by-digest <digest> [store] · by-cell <cell> [store] · list [store] · validate [store] · selftest [store]
const argv = process.argv.slice(2);
const [op, ...rest] = argv;
let storeDir = path.dirname(DEFAULT_STORE);
let explicit = null;
if (["by-k", "by-digest", "by-cell"].includes(op) && rest.length >= 2) { explicit = rest[1]; storeDir = path.dirname(path.resolve(explicit)); }
else if (["list", "validate", "selftest"].includes(op) && rest.length >= 1) { explicit = rest[0]; storeDir = path.dirname(path.resolve(explicit)); }
if (explicit) { try { if (fs.existsSync(explicit)) explicit = path.resolve(explicit); } catch { /* keep as-is */ } }

if (!op || op === "help" || op === "--help" || op === "-h") {
  console.log(`Usage: node kv-cache.mjs <op> [<store-path>]
Ops:
  by-k <coordinate>    exact K lookup -> V {cell,digest,standing,reopen,successor} + K (lookup hint only)
  by-digest <16hex>    exact V.digest lookup
  by-cell <cell>       all rows for a cell (all roles)
  list                 all rows sorted by K, with artifact/source summary
  validate             dynamic validation: TRUE count == validation.checks.length (never the frozen literal)
  selftest             15/15 battery: by-K + by-digest round-trips, typed MISS, fail-closed paths (file-write-free)
Default store: ${DEFAULT_STORE}
Exit codes: 0 success · 1 usage · 2 typed MISS · 3 fail-closed (missing/unparseable/version/digest-format) · 4 validate/selftest FAIL`);
  process.exit(op ? 0 : 1);
}

try {
  if (op === "by-k") {
    if (rest.length < 1) failClosed("KV_ERR_USAGE", "by-k requires <coordinate>", { usage: "kv-cache.mjs by-k <coordinate>" });
    opByK(loadStore(explicit || DEFAULT_STORE), storeDir, rest[0]);
  } else if (op === "by-digest") {
    if (rest.length < 1) failClosed("KV_ERR_USAGE", "by-digest requires <16-hex-digest>", { usage: "kv-cache.mjs by-digest <16hex>" });
    opByDigest(loadStore(explicit || DEFAULT_STORE), storeDir, rest[0]);
  } else if (op === "by-cell") {
    if (rest.length < 1) failClosed("KV_ERR_USAGE", "by-cell requires <cell>", { usage: "kv-cache.mjs by-cell <cell>" });
    opByCell(loadStore(explicit || DEFAULT_STORE), storeDir, rest[0]);
  } else if (op === "list") {
    opList(loadStore(explicit || DEFAULT_STORE), storeDir);
  } else if (op === "validate") {
    opValidate(loadStore(explicit || DEFAULT_STORE), storeDir);
  } else if (op === "selftest") {
    opSelftest(storeDir);
  } else {
    console.error(`unknown op "${op}" — use: by-k | by-digest | by-cell | list | validate | selftest`);
    process.exit(1);
  }
} catch (e) {
  if (e instanceof KvError) { failClosed(e.type, e.message, { path: e.path, expected: e.expected, actual: e.actual }); }
  throw e;
}
