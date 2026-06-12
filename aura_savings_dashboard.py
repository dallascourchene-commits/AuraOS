"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Transparent Accounting / Visible Impact)
DEPENDENCIES: json, os, http.server, aura_savings_db
FUNCTIONS: SavingsDashboard, serve, api_summary, api_recent, api_lifetime
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Savings Dashboard — lightweight HTTP server + interactive UI.
=================================================================

Serves an interactive HTML dashboard at http://localhost:8700 that shows
every LLM call's impact in real time: tokens saved, cost saved, per-provider
breakdowns, time-series charts, and a live feed of recent calls.

No external dependencies required — uses only Python stdlib (http.server +
json) and the existing aura_savings_db module for data.

Run:
    python3 aura_savings_dashboard.py              # start on :8700
    python3 aura_savings_dashboard.py --port 9000  # custom port
    python3 aura_savings_dashboard.py --host 0.0.0.0  # bind all interfaces

Then open http://localhost:8700 in any browser.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aura_Memory")
DB_PATH = os.path.join(MEMORY_DIR, "aura_savings.db")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8700

# ── HTML (inline, no external dependencies) ───────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Aura Savings Dashboard</title>
<style>
:root {
  --bg: #0a0a0f;
  --card: #14141f;
  --border: #2a2a3f;
  --text: #c8c8d8;
  --text-dim: #7878a0;
  --green: #00e676;
  --green-dim: #004d40;
  --gold: #ffab00;
  --gold-dim: #4a3500;
  --red: #ff5252;
  --blue: #448aff;
  --font: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font); background: var(--bg); color: var(--text); padding: 20px; }
h1 { font-size: 1.4em; color: var(--green); margin-bottom: 4px; }
.subtitle { color: var(--text-dim); font-size: 0.8em; margin-bottom: 24px; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.card .label { color: var(--text-dim); font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
.card .value { font-size: 1.8em; font-weight: 700; }
.card .value.saved { color: var(--green); }
.card .value.cost  { color: var(--gold); }
.card .value.count { color: var(--blue); }
.card .value.error { color: var(--red); }
.card .delta { color: var(--text-dim); font-size: 0.75em; margin-top: 4px; }

.section-title { font-size: 1em; color: var(--green); margin: 24px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }

.chart-container { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; overflow-x: auto; }
.chart-container canvas { width: 100%; max-height: 280px; }

table { width: 100%; border-collapse: collapse; font-size: 0.8em; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--text-dim); text-transform: uppercase; font-size: 0.75em; letter-spacing: 0.5px; }
td { color: var(--text); }
tr:hover td { background: rgba(255,255,255,0.03); }
.saved-positive { color: var(--green); }
.saved-negative { color: var(--red); }

.live-feed { max-height: 400px; overflow-y: auto; }
.live-feed .entry { padding: 6px 10px; border-left: 2px solid var(--border); margin-bottom: 4px; font-size: 0.75em; }
.live-feed .entry.gen { border-left-color: var(--blue); }
.live-feed .entry.int { border-left-color: var(--green); }
.live-feed .entry .ts { color: var(--text-dim); }
.live-feed .entry .prov { color: var(--gold); }

.row { display: flex; gap: 16px; flex-wrap: wrap; }
.col { flex: 1; min-width: 300px; }

#status { color: var(--text-dim); font-size: 0.7em; margin-top: 8px; }

.sparkline { display: flex; align-items: flex-end; gap: 2px; height: 40px; }
.sparkline div { flex: 1; background: var(--green); opacity: 0.7; border-radius: 2px 2px 0 0; min-height: 2px; }
</style>
</head>
<body>
<h1>&#9874; AURA SAVINGS DASHBOARD</h1>
<div class="subtitle">Every LLM call logged. Every dollar tracked. Savings made visible.</div>

<div class="grid" id="kpi-grid">
  <div class="card">
    <div class="label">Total LLM Calls</div>
    <div class="value count" id="kpi-calls">--</div>
  </div>
  <div class="card">
    <div class="label">Tokens Saved</div>
    <div class="value saved" id="kpi-tokens-saved">--</div>
    <div class="delta" id="kpi-tokens-delta"></div>
  </div>
  <div class="card">
    <div class="label">Cost Saved (USD)</div>
    <div class="value saved" id="kpi-cost-saved">--</div>
    <div class="delta" id="kpi-cost-delta"></div>
  </div>
  <div class="card">
    <div class="label">Total Spend (USD)</div>
    <div class="value cost" id="kpi-spend">--</div>
  </div>
  <div class="card">
    <div class="label">Errors / Failures</div>
    <div class="value error" id="kpi-errors">--</div>
  </div>
</div>

<div class="row">
  <div class="col">
    <div class="section-title">&#9776; PER PROVIDER</div>
    <table id="provider-table">
      <thead><tr><th>Provider</th><th>Calls</th><th>Spend</th><th>Saved</th><th>Avg Latency</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="col">
    <div class="section-title">&#9733; PER ASPECT</div>
    <table id="aspect-table">
      <thead><tr><th>Aspect</th><th>Calls</th><th>Spend</th><th>Saved</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<div class="section-title">&#9776; DAILY SAVINGS TREND</div>
<div class="chart-container">
  <canvas id="daily-chart"></canvas>
</div>

<div class="section-title">&#9776; LIVE CALL FEED (most recent)</div>
<div class="live-feed" id="live-feed">Loading...</div>

<div id="status">Connecting...</div>

<script>
// ── Simple bar chart (zero-dependency) ──────────────────────────────────
function drawBarChart(canvasId, labels, savedValues, costValues) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  const W = rect.width - 32;
  const H = 240;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  ctx.scale(dpr, dpr);

  const pad = { top: 16, right: 16, bottom: 32, left: 48 };
  const pw = (W - pad.left - pad.right) / Math.max(labels.length, 1);
  const maxVal = Math.max(1, ...savedValues, ...costValues);

  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = '#2a2a3f';
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (H - pad.top - pad.bottom) * (i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#7878a0'; ctx.font = '10px monospace'; ctx.fillText('$' + (maxVal * (1 - i/4)).toFixed(3), 2, y + 4);
  }

  // Bars
  const barW = Math.max(2, pw * 0.35);
  labels.forEach((label, i) => {
    const x = pad.left + i * pw + pw * 0.1;
    // Cost bar (gold)
    const costH = (costValues[i] / maxVal) * (H - pad.top - pad.bottom);
    ctx.fillStyle = '#ffab00';
    ctx.fillRect(x, H - pad.bottom - costH, barW, costH);
    // Saved bar (green, on top)
    const savedH = (savedValues[i] / maxVal) * (H - pad.top - pad.bottom);
    ctx.fillStyle = '#00e676';
    ctx.fillRect(x + barW + 2, H - pad.bottom - savedH, barW, savedH);
    // Label
    ctx.fillStyle = '#7878a0'; ctx.font = '9px monospace'; ctx.textAlign = 'center';
    ctx.fillText(label, x + barW, H - 4);
  });
}

// ── Formatting helpers ──────────────────────────────────────────────────
function fmtUSD(v) { return '$' + (typeof v === 'number' ? v.toFixed(6) : v); }
function fmtNum(v) { return typeof v === 'number' ? v.toLocaleString() : v; }
function fmtLat(v) { return typeof v === 'number' ? v.toFixed(2) + 's' : v; }
function fmtPct(part, total) { if (!total) return ''; const p = (part / total * 100); return p >= 0 ? '+' + p.toFixed(1) + '%' : p.toFixed(1) + '%'; }

// ── Data fetching ───────────────────────────────────────────────────────
async function fetchJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
  return r.json();
}

async function refresh() {
  try {
    const [summary, lifetime, recent] = await Promise.all([
      fetchJSON('/api/summary'),
      fetchJSON('/api/lifetime'),
      fetchJSON('/api/recent?limit=40'),
    ]);

    // KPI cards
    document.getElementById('kpi-calls').textContent = fmtNum(summary.overall.total_calls);
    document.getElementById('kpi-tokens-saved').textContent = fmtNum(summary.overall.total_tokens_saved);
    document.getElementById('kpi-cost-saved').textContent = fmtUSD(summary.overall.total_cost_saved_usd);
    document.getElementById('kpi-spend').textContent = fmtUSD(summary.overall.total_cost_usd);
    document.getElementById('kpi-errors').textContent = fmtNum(summary.overall.error_count);

    // Token delta
    const tokPct = fmtPct(summary.overall.total_tokens_saved, summary.overall.total_prompt_tokens + summary.overall.total_output_tokens);
    document.getElementById('kpi-tokens-delta').textContent = tokPct + ' of total tokens';

    // Cost delta
    const costPct = fmtPct(summary.overall.total_cost_saved_usd, summary.overall.total_cost_usd + summary.overall.total_cost_saved_usd);
    document.getElementById('kpi-cost-delta').textContent = costPct + ' avoided';

    // Per-provider table
    const ptbody = document.querySelector('#provider-table tbody');
    ptbody.innerHTML = (summary.per_provider || []).map(r =>
      '<tr>' +
      '<td>' + r.provider + '</td>' +
      '<td>' + fmtNum(r.calls) + '</td>' +
      '<td>' + fmtUSD(r.cost_usd) + '</td>' +
      '<td class="saved-positive">' + fmtUSD(r.cost_saved_usd) + '</td>' +
      '<td>' + fmtLat(r.avg_latency_sec) + '</td>' +
      '</tr>'
    ).join('');

    // Per-aspect table
    const atbody = document.querySelector('#aspect-table tbody');
    atbody.innerHTML = (summary.per_aspect || []).map(r =>
      '<tr>' +
      '<td>' + (r.aspect || 'unknown') + '</td>' +
      '<td>' + fmtNum(r.calls) + '</td>' +
      '<td>' + fmtUSD(r.cost_usd) + '</td>' +
      '<td class="saved-positive">' + fmtUSD(r.cost_saved_usd) + '</td>' +
      '</tr>'
    ).join('');

    // Daily chart
    const days = summary.per_day || [];
    drawBarChart('daily-chart',
      days.map(d => d.day.slice(5)),
      days.map(d => d.cost_saved_usd || 0),
      days.map(d => d.cost_usd || 0)
    );

    // Live feed
    const feed = document.getElementById('live-feed');
    feed.innerHTML = (recent || []).map(r => {
      const errClass = r.error ? ' style="color:#ff5252"' : '';
      const cls = r.call_type === 'interpret' ? 'int' : 'gen';
      const savedClass = r.cost_saved_usd > 0 ? 'saved-positive' : (r.cost_saved_usd < 0 ? 'saved-negative' : '');
      return '<div class="entry ' + cls + '">' +
        '<span class="ts">' + (r.ts || '') + '</span> ' +
        '<span class="prov">[' + r.provider + '/' + r.model + ']</span> ' +
        (r.task || '') + (r.aspect ? ':' + r.aspect + ' ' : ' ') +
        'in=' + r.prompt_tokens + ' out=' + r.output_tokens + ' ' +
        'cost=' + fmtUSD(r.cost_usd) + ' ' +
        '<span class="' + savedClass + '">saved=' + fmtUSD(r.cost_saved_usd) + '</span> ' +
        'lat=' + fmtLat(r.latency_sec) +
        (r.error ? '<span' + errClass + '> ERR: ' + r.error + '</span>' : '') +
        '</div>';
    }).join('') || '<div style="color:var(--text-dim)">No calls recorded yet.</div>';

    // Lifetime stats in subtitle
    if (lifetime && lifetime.first_call) {
      document.getElementById('status').textContent =
        'Tracking since ' + lifetime.first_call + ' | ' +
        lifetime.total_calls + ' total calls | ' +
        '$' + (lifetime.total_cost_saved_usd || 0).toFixed(4) + ' total saved';
    } else {
      document.getElementById('status').textContent = 'Connected. Waiting for LLM calls...';
    }
  } catch (e) {
    document.getElementById('status').textContent = 'Error: ' + e.message;
  }
}

// Auto-refresh every 5 seconds
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""

# ── HTTP request handler ──────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    """Serves the dashboard HTML + JSON API endpoints."""

    def log_message(self, format, *args):
        pass  # quiet

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_db(self):
        from aura_savings_db import SavingsDB
        return SavingsDB(DB_PATH)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            self._send_html(DASHBOARD_HTML)

        elif path == "/api/summary":
            try:
                db = self._get_db()
                self._send_json(db.summary())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/lifetime":
            try:
                db = self._get_db()
                self._send_json(db.lifetime_totals())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/recent":
            try:
                from urllib.parse import urlparse, parse_qs
                qs = parse_qs(urlparse(self.path).query)
                limit = int(qs.get("limit", [50])[0])
                db = self._get_db()
                self._send_json(db.recent_calls(limit=min(limit, 200)))
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/health":
            self._send_json({"status": "ok", "ts": time.time()})

        else:
            self._send_json({"error": "not found"}, 404)


def main(argv: list[str] | None = None) -> int:
    global DB_PATH
    p = argparse.ArgumentParser(description="Aura Savings Dashboard server")
    p.add_argument("--host", default=DEFAULT_HOST, help=f"bind host (default: {DEFAULT_HOST})")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default: {DEFAULT_PORT})")
    p.add_argument("--db", default=DB_PATH, help="path to savings.db")
    args = p.parse_args(argv)

    DB_PATH = args.db

    server = HTTPServer((args.host, args.port), DashboardHandler)
    print(f"[AURA SAVINGS DASHBOARD] http://{args.host}:{args.port}")
    print(f"[*] database: {DB_PATH}")
    print("[*] Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] shutting down")
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())