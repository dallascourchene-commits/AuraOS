"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f9-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: sys, collections, struct, json
FUNCTIONS: execute_dag_plan
SYNOPSIS: `Aura OS Auditor: The Python module provides a strict, single-sentence technical synopsis for a Python module with dependencies [sys, collections, struct, json] and functions [execute_dag_plan].`
[/AURA_MASTER_KEY]
"""
import sys
import json
import struct
from collections import deque

def execute_dag_plan():
    # STEP 1: Binary IPC Strict Ingestion
    try:
        # 1. Read and clear the 16-byte hardware activator token to align the stream
        activator = sys.stdin.buffer.read(16)
        if not activator or len(activator) < 16:
            sys.stderr.write("Error: Missing or truncated hardware activator token\n")
            sys.exit(1)

        # 2. Read the 4-byte length prefix (Little Endian)
        prefix = sys.stdin.buffer.read(4)
        if not prefix or len(prefix) < 4:
            sys.stderr.write("Error: Empty or invalid binary input prefix\n")
            sys.exit(1)
        
        # Unpack the 4-byte unsigned int to get the exact payload size
        payload_len = struct.unpack('<I', prefix)[0]
        
        # Read the exact payload bytes directly from the buffer
        raw_data = sys.stdin.buffer.read(payload_len)
        
        # Decode the bytes back to a dictionary
        dag_data = json.loads(raw_data.decode('utf-8'))
        nodes_data = dag_data.get("nodes", [])
        edges_data = dag_data.get("edges", [])
        
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Error: Invalid JSON structure ({str(e)})\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error: Ingestion exception ({str(e)})\n")
        sys.exit(1)

    # STEP 2: Kahn's Algorithm (Mathematical Execution Tree)
    nodes = [n.get("id") for n in nodes_data if "id" in n]
    edges = [(e.get("from"), e.get("to")) for e in edges_data if "from" in e and "to" in e]

    in_degree = {node: 0 for node in nodes}
    adj = {node: [] for node in nodes}

    for u, v in edges:
        if u not in adj: adj[u] = []
        if v not in adj: adj[v] = []
        if u not in in_degree: in_degree[u] = 0
        if v not in in_degree: in_degree[v] = 0
        
        adj[u].append(v)
        in_degree[v] += 1

    queue = deque([node for node in nodes if in_degree[node] == 0])
    topo_order = []

    while queue:
        u = queue.popleft()
        topo_order.append(u)

        for v in adj.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    # STEP 3: Mathematical Cycle Verification
    if len(topo_order) != len(nodes):
        print(json.dumps({"status": "cycle detected"}))
    else:
        print(json.dumps({"status": "success", "execution_path": topo_order}))

if __name__ == "__main__":
    execute_dag_plan()
