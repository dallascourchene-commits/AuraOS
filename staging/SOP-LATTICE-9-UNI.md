# AURA-OS UNIVERSAL WORK ORDER: TRIADIC 9-LATTICE CRYSTALLIZATION PROTOCOL

**Document ID:** `SOP-LATTICE-9-UNI`

**Execution Context:** Shared Staging Workspace (`./staging/`)

**Hydration Scope:** $L_0 \longleftrightarrow L_4$

**Cycle Cadence:** 60s Polling Loop

## Node Identity & Fractal Coordinate Map

Each agent instance self-binds by reading its assigned worker ID (`W1`–`W9`). The 9-lattice operates as three interconnected triads (Meso-Lattice), decomposing recursively to individual execution steps (Micro) and system-wide state sync (Macro).

```text
          [ Triad α: Ingestion & Decomposition ]
                   W1 (Apex / Ingress)
                  /  \
            W2 (Parse)  W3 (Route)
                 /      \
 [ Triad β: Core Execution ]    [ Triad γ: Verification & Sync ]
         W4 (Hydrate L3)               W7 (Audit / Delta)
        /              \              /               \
 W5 (Transform L4)   W6 (Compile)   W8 (Verify L1)   W9 (Crystallize L0)
```

| Slot ID | Lattice Position | Functional Role | Upstream Ingest | Downstream Target | Hydration Bounds |
|---|---|---|---|---|---|
| **W1** | $\text{Triad } \alpha \text{ [Root]}$ | Task Ingestion & Semantic Decomp | User / System Trigger | W2, W3 | $L_0 \to L_1$ |
| **W2** | $\text{Triad } \alpha \text{ [Left]}$ | Structural AST / Interface Typing | W1 | W4 | $L_1 \to L_2$ |
| **W3** | $\text{Triad } \alpha \text{ [Right]}$ | Dependency & Graph Routing | W1 | W6 | $L_1 \to L_2$ |
| **W4** | $\text{Triad } \beta \text{ [Left]}$ | Context & Memory Hydration | W2 | W5 | $L_2 \to L_3$ |
| **W5** | $\text{Triad } \beta \text{ [Core]}$ | Verbatim Artifact Execution/Write | W4 | W6, W7 | $L_3 \to L_4$ |
| **W6** | $\text{Triad } \beta \text{ [Right]}$ | Unit Assembly & Intermediate Build | W3, W5 | W8 | $L_4 \to L_3$ |
| **W7** | $\text{Triad } \gamma \text{ [Left]}$ | State Audit, Schema Invariance Check | W5 | W8 | $L_4 \to L_2$ |
| **W8** | $\text{Triad } \gamma \text{ [Core]}$ | Contract Verification & Test Pass | W6, W7 | W9 | $L_2 \to L_1$ |
| **W9** | $\text{Triad } \gamma \text{ [Apex]}$ | Ledger Crystallization & $L_0$ Commit | W8 | Shared Staging Index | $L_1 \to L_0$ |

## Hydration Layer Architecture

Agents must never load higher hydration layers into memory than their immediate transformation step requires.

- **$L_0$ — Symbolic / Hash Primitive:** Canonical CID / content hash, state token, atomic status flag (`QUEUED`, `PROCESSING`, `CRYSTALLIZED`).
- **$L_1$ — Structural Schema:** Type definitions, function signatures, JSON schemas, interface boundaries.
- **$L_2$ — Dependency Graph:** Edge routes, symbol call graphs, localized routing matrices.
- **$L_3$ — Operational State Ledger:** Working contextual memory, local variables, hydrated state diffs.
- **$L_4$ — Concrete Verbatim Artifact:** Full source code, binary payloads, raw text assets, compiled filesystem outputs.

## Universal Agent Execution Lifecycle

Place this exact runbook into each agent terminal window. When launching, supply only: `export WORKER_ID=W[1-9]`.

```bash
#!/usr/bin/env bash
# Universal Worker Daemon - 60s Cadence
echo "[*] Initializing Lattice Worker: $WORKER_ID"

while true; do
  LEDGER="./staging/state_ledger.json"
  ORDER="./staging/work_orders/${WORKER_ID}.json"

  if [ -f "$ORDER" ]; then
    STATUS=$(jq -r '.status' "$ORDER" 2>/dev/null)
    
    if [ "$STATUS" == "PENDING" ]; then
      echo "[+] Work order detected for $WORKER_ID. Processing..."
      
      # 1. Update State -> PROCESSING
      jq '.status = "PROCESSING" | .timestamp = now' "$ORDER" > "${ORDER}.tmp" && mv "${ORDER}.tmp" "$ORDER"
      
      # 2. Execute Local Hydration & Transformation
      # (Agent reads upstream dependencies from staging, executes role-specific transform)
      
      # 3. Write Artifact / Crystallize
      # (Agent deposits L(N) artifact into ./staging/artifacts/)
      
      # 4. Mark Complete & Forward Downstream Signal
      jq '.status = "CRYSTALLIZED" | .updated_at = now' "$ORDER" > "${ORDER}.tmp" && mv "${ORDER}.tmp" "$ORDER"
      echo "[✓] Phase complete. Output crystallized to staging."
    fi
  fi

  echo "[-] $WORKER_ID entering steady state. Polling in 60s..."
  sleep 60
done
```

## Master Staging Work Order Schema (`./staging/work_orders/WN.json`)

```json
{
  "work_order_id": "WO-20260816-001",
  "worker_slot": "W5",
  "triad": "BETA",
  "hydration_in": "L3",
  "hydration_out": "L4",
  "status": "PENDING",
  "upstream_dependencies": [
    "WO-20260816-001-W4"
  ],
  "payload": {
    "target_module": "core/routing/transducer",
    "directive": "Execute full implementation of the 6-slot FST transition table",
    "inputs": "./staging/artifacts/W4_context_hydrated.json",
    "output_dest": "./staging/artifacts/W5_verbatim_source.rs"
  },
  "invariants": [
    "Memory footprint must strictly enforce <4GB boundary",
    "Zero-allocation transitions on hot path"
  ],
  "signatures": {
    "l0_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
}
```

## Deployment Runbook

1. **Bootstrap Workspace:** Ensure directory tree `./staging/{work_orders,artifacts,ledgers}` exists.
2. **Initialize Shared State:** Create `./staging/state_ledger.json` holding global slot availability.
3. **Dispatch Terminal Windows:** Open 9 separate windows (`W1` through `W9`).
4. **Export Identity:** Run `export WORKER_ID=W<N>` in each respective terminal.
5. **Start Daemon:** Execute the lifecycle loop script in all windows.
6. **Trigger Pipeline:** Drop the root task payload into `./staging/work_orders/W1.json` with status `PENDING`. The lattice will cascade through $\alpha \to \beta \to \gamma$ automatically.

---

## W3 Staging Note

This file preserves the supplied SOP. W3's separate L2 routing receipt records executability gaps found by static inspection of the supplied daemon. Those findings do not alter this source document.
