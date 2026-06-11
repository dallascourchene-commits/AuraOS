"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MINWAAJIMO (Logic-to-Light Bridge)
DEPENDENCIES: asyncio, json, websockets, aura_topological_scanner, aura_topology_ws_bridge
FUNCTIONS: UnrealBridge, broadcast_topology, start_bridge_server
SYNOPSIS: WebSocket bridge that maps AuraOS polysynthetic topology data to 3D
          viewport coordinates for Unreal Engine, Unity, or WebGL clients.
          Implements the "Logic-to-Light" pattern: Aura is the brain,
          external renderers are passive canvases receiving coordinate updates.
[/AURA_MASTER_KEY]
"""
import asyncio
import json
import os

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment,misc]

# Try to import the AR WebSocket server for shared broadcast path
try:
    from aura_topology_ws_bridge import AuraARWebSocketServer
except ImportError:
    AuraARWebSocketServer = None  # type: ignore[assignment]


class UnrealBridge:
    """
    Stateless bridge between AuraOS topology data and external 3D viewport
    clients (Unreal Engine, Unity, WebGL browser canvas).

    Implements the "Symbolic CPU-Splatting" approach:
    - Each function/class/module maps to a geometric primitive.
    - Position = semantic vector in phasor space.
    - Color = resonance health (green = stable, red = drift).
    - Scale = code complexity (lines-of-code / AST depth).

    The bridge sends lightweight coordinate payloads over WebSockets —
    the 3D client is responsible for instantiating and updating meshes.
    No GPU is needed on the AuraOS side.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8081):
        self.host = host
        self.port = port
        self._server = None
        self._clients: set = set()

    # ── Topology ingest ───────────────────────────────────────────────────
    def map_topology_to_viewport(self, topology_data: dict) -> dict:
        """
        Convert raw live_topology_ast.json data into a viewport-ready
        payload with per-node color, scale, and position.

        Returns a dict structured for 3D client consumption:
            {
              "type": "RECONSTRUCT",
              "nodes": [ {id, label, position, color, scale, shape}, ... ],
              "edges": [ {source, target, color, width}, ... ],
              "frame": "AURA_MANIFOLD_v1"
            }
        """
        nodes = topology_data.get("nodes", [])
        edges = topology_data.get("edges", [])

        viewport_nodes = []
        for node in nodes:
            node_id = node.get("id", "")
            label = node.get("label", "?")
            # Default position from the topology scanner's vector field
            pos = node.get("vector", [0.0, 0.0, 0.0])
            # Ensure position is a flat [x, y, z] list of floats
            if isinstance(pos, (list, tuple)):
                pos = [float(p) for p in pos[:3]]
            else:
                pos = [float(pos), 0.0, 0.0]
            # Pad to exactly 3 elements
            while len(pos) < 3:
                pos.append(0.0)

            # Color coding: green=healthy, red=drift, cyan=standard
            color = node.get("color", "#00E5FF")
            # Scale from function complexity (heuristic: node count proxy)
            # If the node carries a "line" count or similar, use it
            scale = 1.0
            meta = node.get("metadata", {})
            ast_data = meta.get("ast_data", {})
            if isinstance(ast_data, dict):
                line_count = ast_data.get("line_count", 0)
                if line_count and line_count > 0:
                    scale = min(3.0, max(0.5, line_count / 50.0))

            shape = node.get("shape", "Sphere")

            viewport_nodes.append({
                "id": node_id,
                "label": label,
                "position": pos,
                "color": color,
                "scale": scale,
                "shape": shape,
            })

        viewport_edges = []
        for edge in edges:
            viewport_edges.append({
                "source": edge.get("source", ""),
                "target": edge.get("target", ""),
                "color": edge.get("color", "#FFFFFF"),
                "width": float(edge.get("strength", 0.1)),
                "type": edge.get("type", "unknown"),
            })

        return {
            "type": "RECONSTRUCT",
            "nodes": viewport_nodes,
            "edges": viewport_edges,
            "frame": "AURA_MANIFOLD_v1",
        }

    # ── WebSocket handlers ────────────────────────────────────────────────
    async def _client_handler(self, websocket):
        """
        Per-client handler. On connect: push current topology.
        On message: handle commands (update_node, request_refresh, ping).
        """
        self._clients.add(websocket)
        remote = getattr(websocket, "remote_address", "?")
        print(f"[UNREAL BRIDGE] Client connected from {remote}")

        try:
            # Push current topology on connect
            await self.broadcast_current_topology(websocket)

            async for raw_msg in websocket:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_message(websocket, msg)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"type": "ERROR", "message": "Invalid JSON"}))
                except Exception as exc:
                    await websocket.send(json.dumps({"type": "ERROR", "message": str(exc)}))
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            print(f"[UNREAL BRIDGE] Client disconnected from {remote}")

    async def _handle_message(self, websocket, msg: dict) -> None:
        msg_type = msg.get("type", "")
        if msg_type == "PING":
            await websocket.send(json.dumps({"type": "PONG"}))
        elif msg_type == "REQUEST_TOPOLOGY":
            await self.broadcast_current_topology(websocket)
        elif msg_type == "UPDATE_NODE":
            # Clients can request a node be re-colorized or scaled
            node_id = msg.get("nodeId")
            if node_id:
                echo = {
                    "type": "NODE_UPDATE_ACK",
                    "nodeId": node_id,
                    "status": "acknowledged",
                }
                await websocket.send(json.dumps(echo))
                print(f"[UNREAL BRIDGE] Node update request: {node_id}")
        else:
            await websocket.send(json.dumps({"type": "ERROR", "message": f"Unknown type: {msg_type}"}))

    async def broadcast_current_topology(self, target_ws=None) -> None:
        """
        Read live_topology_ast.json, convert to viewport format, and send.

        If target_ws is provided, send only to that client.
        Otherwise, fan-out to all connected clients.
        """
        topology_path = "Aura_Memory/live_topology_ast.json"
        if not os.path.exists(topology_path):
            payload = {"type": "TOPOLOGY_UPDATE", "data": {"nodes": [], "edges": []}}
        else:
            try:
                with open(topology_path, "r", encoding="utf-8") as f:
                    topology_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                topology_data = {"nodes": [], "edges": []}
            viewport_data = self.map_topology_to_viewport(topology_data)
            payload = {"type": "TOPOLOGY_UPDATE", "data": viewport_data}

        raw_payload = json.dumps(payload)

        if target_ws is not None:
            try:
                await target_ws.send(raw_payload)
            except Exception:
                pass
        else:
            dead = set()
            for client in list(self._clients):
                try:
                    await client.send(raw_payload)
                except Exception:
                    dead.add(client)
            for d in dead:
                self._clients.discard(d)

    # ── Broadcast (gist-style simple API) ─────────────────────────────────
    async def broadcast_topology(self, topology_data: dict):
        """
        Simplified broadcast method matching the gist's API pattern.
        Converts topology_data to viewport format and fans out.
        """
        viewport_data = self.map_topology_to_viewport(topology_data)
        payload = json.dumps(viewport_data)
        dead = set()
        for client in list(self._clients):
            try:
                await client.send(payload)
            except Exception:
                dead.add(client)
        for d in dead:
            self._clients.discard(d)

    # ── Lifecycle ─────────────────────────────────────────────────────────
    async def start(self) -> None:
        """Start the WebSocket bridge server."""
        if websockets is None:
            raise ImportError(
                "websockets is required for UnrealBridge (pip install websockets)"
            )
        self._server = await websockets.serve(
            self._client_handler, self.host, self.port
        )
        print(f"[UNREAL BRIDGE] Server online at ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Graceful shutdown."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._clients.clear()


# ── Standalone entry point ───────────────────────────────────────────────────
async def main():
    bridge = UnrealBridge(host="0.0.0.0", port=8081)
    await bridge.start()
    print("[UNREAL BRIDGE] Running — press Ctrl+C to stop.")
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())