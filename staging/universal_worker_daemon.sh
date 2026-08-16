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
