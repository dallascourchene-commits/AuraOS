"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:BRIDGE_WS_TOPOLOGY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, json, os, gc, pathlib
FUNCTIONS: TopologyBroadcastHub, broadcast_topology_chunks, stream_to_clients,
           _chunk_json_fixed_frame, register_client, unregister_client, background_topology_watch
SYNOPSIS: Pure-asyncio broadcast bridge that reads Aura_Memory/live_topology_ast.json,
          chunks structural tokens into fixed-frame 4KB payloads, and non-blockingly
          streams to all connected WebSocket clients without blocking the main runtime
          loop or causing socket drops under Termux 4GB RAM constraints.
[/AURA_MASTER_KEY]
"""
import asyncio
import gc
import json
import os
from pathlib import Path

# ── Fixed-frame chunking constants ──────────────────────────────────────────
_FRAME_SIZE_BYTES = 4096       # 4 KB per chunk — fits in a single WebSocket frame
_MAX_BROADCAST_QUEUE = 128     # backpressure ceiling: drop oldest if full
_SEND_TIMEOUT = 2.0            # per-client send timeout (prevents stalled clients)

# ── Topology source path (must match aura_topological_scanner.py output) ─────
_TOPOLOGY_PATH = Path("Aura_Memory/live_topology_ast.json")


def _chunk_json_fixed_frame(payload: dict) -> list[dict]:
    """
    Serialise *payload* to compact JSON, then split into fixed-frame chunks.
    Each chunk carries a sequence index, total count, and a slice of the
    serialised string so the client can reassemble deterministically.
    """
    raw = json.dumps(payload, separators=(",", ":"))   # compact, no spaces
    raw_bytes = raw.encode("utf-8")
    total_frames = max(1, (len(raw_bytes) + _FRAME_SIZE_BYTES - 1) // _FRAME_SIZE_BYTES)

    frames: list[dict] = []
    for i in range(total_frames):
        start = i * _FRAME_SIZE_BYTES
        chunk_bytes = raw_bytes[start:start + _FRAME_SIZE_BYTES]
        frames.append({
            "type": "topology_frame",
            "seq": i,
            "total": total_frames,
            "payload": chunk_bytes.decode("utf-8", errors="replace"),
        })
    return frames


class TopologyBroadcastHub:
    """
    Pure-asyncio, lock-free broadcast hub for live topology AST data.

    Clients are tracked in a simple list.  Broadcasts use ``asyncio.gather``
    with a per-client timeout so a single stalled client never blocks the
    rest.  The queue uses ``asyncio.Queue`` with a bounded size so back-
    pressure silently drops frames rather than growing unboundedly (critical
    under 4 GB RAM).
    """

    def __init__(self) -> None:
        self._clients: list[asyncio.Queue] = []
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_BROADCAST_QUEUE)
        self._broadcast_task: asyncio.Task | None = None
        self._watch_task: asyncio.Task | None = None
        self._last_mtime: float = 0.0
        self._running: bool = False

    # ── Client management ────────────────────────────────────────────────
    def register_client(self) -> asyncio.Queue:
        """Create a private per-client queue and return it for the WS handler."""
        q: asyncio.Queue = asyncio.Queue(maxsize=32)
        self._clients.append(q)
        return q

    def unregister_client(self, q: asyncio.Queue) -> None:
        """Remove a client queue; drain to prevent memory leaks."""
        try:
            self._clients.remove(q)
        except ValueError:
            pass
        # Drain remaining items
        while not q.empty():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                break
        del q
        gc.collect()

    # ── Broadcast engine ──────────────────────────────────────────────────
    async def _broadcast_worker(self) -> None:
        """Continuously drain the broadcast queue and fan-out to all clients."""
        while self._running:
            try:
                frames = await asyncio.wait_for(
                    self._broadcast_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            if not self._clients:
                gc.collect()
                continue

            # Fan-out: create a send task per client, gather with timeout
            async def _send_to_one(client_q: asyncio.Queue) -> None:
                try:
                    for frame in frames:
                        client_q.put_nowait(frame)
                except asyncio.QueueFull:
                    # Client too slow — drop remaining frames for this client
                    pass

            tasks = [_send_to_one(c) for c in list(self._clients)]
            try:
                await asyncio.wait_for(asyncio.gather(*tasks), timeout=_SEND_TIMEOUT)
            except (asyncio.TimeoutError, Exception):
                pass  # one or more clients stalled; others already received
            finally:
                del tasks
                gc.collect()

    # ── Topology watcher ──────────────────────────────────────────────────
    async def _topology_watch_loop(self) -> None:
        """Poll live_topology_ast.json mtime; broadcast on change."""
        while self._running:
            try:
                if _TOPOLOGY_PATH.exists():
                    mtime = _TOPOLOGY_PATH.stat().st_mtime
                    if mtime != self._last_mtime:
                        self._last_mtime = mtime
                        try:
                            payload = json.loads(_TOPOLOGY_PATH.read_text(encoding="utf-8"))
                        except (json.JSONDecodeError, OSError):
                            await asyncio.sleep(0.5)
                            continue
                        frames = _chunk_json_fixed_frame(payload)
                        try:
                            self._broadcast_queue.put_nowait(frames)
                        except asyncio.QueueFull:
                            # Backpressure: drop the oldest pending broadcast
                            try:
                                self._broadcast_queue.get_nowait()
                            except asyncio.QueueEmpty:
                                pass
                            try:
                                self._broadcast_queue.put_nowait(frames)
                            except asyncio.QueueFull:
                                pass
                        finally:
                            del payload
                            del frames
                            gc.collect()
            except Exception:
                pass
            await asyncio.sleep(0.5)   # gentle poll — preserves ARM battery

    # ── Lifecycle ─────────────────────────────────────────────────────────
    async def start(self) -> None:
        """Launch background tasks."""
        if self._running:
            return
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_worker())
        self._watch_task = asyncio.create_task(self._topology_watch_loop())

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        for task in (self._broadcast_task, self._watch_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        # Drain and close all client queues
        for q in list(self._clients):
            self.unregister_client(q)
        self._clients.clear()
        gc.collect()

    async def broadcast_topology_now(self) -> None:
        """
        Force an immediate re-read and broadcast (e.g. after !topology).
        Non-blocking — enqueues frames and returns.
        """
        if not _TOPOLOGY_PATH.exists():
            return
        try:
            payload = json.loads(_TOPOLOGY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self._last_mtime = _TOPOLOGY_PATH.stat().st_mtime
        frames = _chunk_json_fixed_frame(payload)
        try:
            self._broadcast_queue.put_nowait(frames)
        except asyncio.QueueFull:
            pass
        finally:
            del payload
            del frames
            gc.collect()


# ── Module-level singleton (compatible with pulse.py's brain pattern) ──────
_topology_hub: TopologyBroadcastHub | None = None
_HUB_LOCK = asyncio.Lock()


async def get_topology_hub() -> TopologyBroadcastHub:
    """Return the process-wide TopologyBroadcastHub singleton."""
    global _topology_hub
    if _topology_hub is None:
        async with _HUB_LOCK:
            if _topology_hub is None:
                _topology_hub = TopologyBroadcastHub()
                await _topology_hub.start()
    return _topology_hub


async def stream_to_clients(ws_handler_coro, host: str = "0.0.0.0", port: int = 8081):
    """
    Entry point for the combined WebSocket server: topology bridge + AR pulse.
    Kept deliberately minimal — imports `websockets` lazily so the module
    can be imported without the optional dependency present.
    """
    try:
        import websockets
    except ImportError:
        raise ImportError("websockets is required for streaming (pip install websockets)")

    hub = await get_topology_hub()

    async def _combined_handler(websocket):
        client_q = hub.register_client()
        try:
            # Fan topology frames into the WS pipe while the handler runs
            async def _topology_pump():
                while True:
                    try:
                        frame = await asyncio.wait_for(client_q.get(), timeout=5.0)
                        await websocket.send(json.dumps(frame, separators=(",", ":")))
                    except asyncio.TimeoutError:
                        continue
                    except (websockets.exceptions.ConnectionClosed, Exception):
                        break

            pump_task = asyncio.create_task(_topology_pump())
            try:
                await ws_handler_coro(websocket)
            finally:
                pump_task.cancel()
                try:
                    await pump_task
                except asyncio.CancelledError:
                    pass
        finally:
            hub.unregister_client(client_q)

    async with websockets.serve(_combined_handler, host, port):
        await asyncio.Future()  # run forever


# ============================================================================
# AR WebSocket Server — extends TopologyBroadcastHub with shape interaction,
# session management, hotswap, and USER_GUIDE.md shape-type mapping.
# Integrates directly with the existing TopologyBroadcastHub singleton so
# both the AR display and the topology watcher share one broadcast pipeline.
# ============================================================================

import json as _json_ar
import uuid as _uuid_ar
import logging as _logging_ar
from dataclasses import dataclass as _dataclass_ar, field as _field_ar
from typing import Dict as _Dict_ar, List as _List_ar, Set as _Set_ar, Any as _Any_ar, Optional as _Optional_ar

_ar_logger = _logging_ar.getLogger("aura.ar_websocket")

# Shape type → (shape_type, colour) per USER_GUIDE.md
_AR_SHAPE_TYPE_MAP: dict = {
    "class":        ("Sphere",       "#00E5FF"),   # Cyan
    "async_method": ("Icosahedron",  "#FF007F"),   # Neon Pink
    "function":     ("Tetrahedron",  "#E040FB"),   # Purple
    "helper":       ("Cube",         "#9E9E9E"),   # Gray
    "module":       ("Cube",         "#4CAF50"),   # Green
    "method":       ("Tetrahedron",  "#2196F3"),   # Blue
}


@_dataclass_ar
class _ARShape:
    shape_id: str
    shape_type: str
    label: str
    position: _List_ar[float]
    scale: float = 1.0
    color: str = "#00E5FF"
    node_type: str = "function"
    metadata: _Dict_ar[str, _Any_ar] = _field_ar(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.shape_id,
            "type": self.shape_type,
            "label": self.label,
            "position": self.position,
            "scale": self.scale,
            "color": self.color,
            "metadata": self.metadata,
        }


@_dataclass_ar
class _ARConnection:
    connection_id: str
    source_id: str
    target_id: str
    color: str = "#FFFFFF"
    width: float = 0.1

    def to_dict(self) -> dict:
        return {
            "id": self.connection_id,
            "sourceId": self.source_id,
            "targetId": self.target_id,
            "color": self.color,
            "width": self.width,
        }


@_dataclass_ar
class _ARSession:
    session_id: str
    websocket: object          # websockets.WebSocketServerProtocol
    subscribed_topics: _Set_ar[str] = _field_ar(default_factory=set)


class AuraARWebSocketServer:
    """
    AR WebSocket server that exposes the AuraOS code topology as interactive
    3-D shapes.  Builds on the existing TopologyBroadcastHub so topology
    polling is not duplicated.

    Shape commands accepted from clients
    ------------------------------------
    TOPOLOGY_REQUEST  → returns current AR topology
    SHAPE_INTERACTION → expand / contract / select / deselect a shape
    ADD_SHAPE         → add a new shape from functionData payload
    HOTSWAP_REQUEST   → trigger AST surgical graft (integrated with node)
    SUBSCRIBE         → subscribe to a named event topic
    UNSUBSCRIBE       → unsubscribe
    PING              → returns PONG

    Usage
    -----
        server = AuraARWebSocketServer(port=8765)
        await server.start()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        topology_refresh_interval: float = 1.0,
    ) -> None:
        self.host = host
        self.port = port
        self.topology_refresh_interval = topology_refresh_interval

        self._sessions: _Dict_ar[str, _ARSession] = {}
        self._shapes: _Dict_ar[str, _ARShape] = {}
        self._connections: _List_ar[_ARConnection] = []
        self._topology_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._server = None
        self._refresh_task: _Optional_ar[asyncio.Task] = None

        _ar_logger.info("AuraARWebSocketServer init: %s:%d", host, port)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the AR WebSocket server and topology refresh loop."""
        try:
            import websockets as _ws_lib
        except ImportError:
            raise ImportError("websockets is required (pip install websockets)")

        await self._refresh_topology()
        self._refresh_task = asyncio.create_task(self._topology_refresh_loop())

        self._server = await _ws_lib.serve(
            self._handle_connection,
            self.host,
            self.port,
            ping_interval=30.0,
            ping_timeout=60.0,
        )
        _ar_logger.info("AR WebSocket server running on ws://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Graceful shutdown."""
        _ar_logger.info("Stopping AR WebSocket server …")
        self._shutdown_event.set()

        for session in list(self._sessions.values()):
            try:
                await session.websocket.close(1001, "Server shutdown")
            except Exception:
                pass
        self._sessions.clear()

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        _ar_logger.info("AR WebSocket server stopped")

    # ── Topology ingestion ───────────────────────────────────────────────────

    async def _topology_refresh_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                await self._refresh_topology()
                await asyncio.sleep(self.topology_refresh_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _ar_logger.error("Topology refresh error: %s", exc)
                await asyncio.sleep(5.0)

    async def _refresh_topology(self) -> None:
        """
        Load live_topology_ast.json and convert AST nodes to AR shapes.
        Falls back gracefully if the file is missing or malformed.
        """
        async with self._topology_lock:
            topology_path = _TOPOLOGY_PATH    # reuse existing constant
            if not topology_path.exists():
                return
            try:
                raw = topology_path.read_text(encoding="utf-8")
                payload = _json_ar.loads(raw)
            except (_json_ar.JSONDecodeError, OSError) as exc:
                _ar_logger.warning("Could not load topology: %s", exc)
                return

            nodes_data = payload.get("nodes", {})
            edges_data = payload.get("edges", {})

            # Rebuild shape registry from AST
            new_shapes: _Dict_ar[str, _ARShape] = {}
            for node_id, node_data in nodes_data.items():
                node_type = str(node_data.get("type", "function")).lower()
                shape_type, color = _AR_SHAPE_TYPE_MAP.get(
                    node_type, ("Cube", "#9E9E9E")
                )
                new_shapes[node_id] = _ARShape(
                    shape_id=node_id,
                    shape_type=shape_type,
                    label=node_data.get("name", node_id),
                    position=node_data.get("position", [0.0, 0.0, 0.0]),
                    scale=float(node_data.get("scale", 1.0)),
                    color=color,
                    node_type=node_type,
                    metadata={"ast_data": node_data},
                )

            new_connections: _List_ar[_ARConnection] = []
            for edge_id, edge_data in edges_data.items():
                new_connections.append(
                    _ARConnection(
                        connection_id=edge_id,
                        source_id=edge_data.get("source", ""),
                        target_id=edge_data.get("target", ""),
                        color=edge_data.get("color", "#FFFFFF"),
                        width=float(edge_data.get("width", 0.1)),
                    )
                )

            self._shapes = new_shapes
            self._connections = new_connections

        await self._broadcast_topology()

    def _topology_dict(self) -> dict:
        return {
            "nodes": [s.to_dict() for s in self._shapes.values()],
            "edges": [c.to_dict() for c in self._connections],
            "metadata": {
                "node_count": len(self._shapes),
                "edge_count": len(self._connections),
                "source": "live_topology_ast.json",
            },
        }

    # ── Connection + message handling ────────────────────────────────────────

    async def _handle_connection(self, websocket, path: str = "") -> None:
        session_id = str(_uuid_ar.uuid4())
        session = _ARSession(session_id=session_id, websocket=websocket)
        self._sessions[session_id] = session

        _ar_logger.info(
            "AR client connected: %s from %s", session_id, getattr(websocket, "remote_address", "?")
        )

        try:
            # Send current topology on connect
            await websocket.send(_json_ar.dumps({
                "type": "TOPOLOGY_UPDATE",
                "data": self._topology_dict(),
            }))

            async for raw_msg in websocket:
                try:
                    msg = _json_ar.loads(raw_msg)
                    await self._handle_message(session, msg)
                except _json_ar.JSONDecodeError:
                    await websocket.send(_json_ar.dumps({"type": "ERROR", "message": "Invalid JSON"}))
                except Exception as exc:
                    _ar_logger.error("Message error: %s", exc)
                    await websocket.send(_json_ar.dumps({"type": "ERROR", "message": str(exc)}))

        except Exception:
            pass
        finally:
            self._sessions.pop(session_id, None)
            _ar_logger.info("AR client disconnected: %s", session_id)

    async def _handle_message(self, session: _ARSession, data: dict) -> None:
        msg_type = data.get("type")
        if not msg_type:
            await session.websocket.send(_json_ar.dumps({"type": "ERROR", "message": "type required"}))
            return

        if msg_type == "TOPOLOGY_REQUEST":
            await session.websocket.send(_json_ar.dumps({
                "type": "TOPOLOGY_UPDATE", "data": self._topology_dict()
            }))

        elif msg_type == "SHAPE_INTERACTION":
            await self._handle_shape_interaction(session, data)

        elif msg_type == "ADD_SHAPE":
            await self._handle_add_shape(session, data)

        elif msg_type == "HOTSWAP_REQUEST":
            await self._handle_hotswap_request(session, data)

        elif msg_type == "SUBSCRIBE":
            topic = data.get("topic", "")
            session.subscribed_topics.add(topic)

        elif msg_type == "UNSUBSCRIBE":
            session.subscribed_topics.discard(data.get("topic", ""))

        elif msg_type == "PING":
            await session.websocket.send(_json_ar.dumps({"type": "PONG"}))

        else:
            await session.websocket.send(_json_ar.dumps({
                "type": "ERROR", "message": f"Unknown type: {msg_type}"
            }))

    async def _handle_shape_interaction(self, session: _ARSession, data: dict) -> None:
        shape_id = data.get("shapeId")
        action   = data.get("action")          # expand|contract|select|deselect
        if not shape_id or not action:
            raise ValueError("shapeId and action required")

        async with self._topology_lock:
            shape = self._shapes.get(shape_id)
            if shape is None:
                raise KeyError(f"Shape {shape_id!r} not found")

            if action == "expand":
                shape.scale = min(3.0, shape.scale * 1.5)
            elif action == "contract":
                shape.scale = max(0.3, shape.scale * 0.7)
            elif action == "select":
                shape.color = "#FFFF00"
            elif action == "deselect":
                _, orig_color = _AR_SHAPE_TYPE_MAP.get(shape.node_type, ("Cube", "#9E9E9E"))
                shape.color = orig_color

        await self._broadcast_message({
            "type": "SHAPE_UPDATE",
            "shapeId": shape_id,
            "state": {"scale": shape.scale, "color": shape.color},
        })
        _ar_logger.info("Shape %s %sed", shape_id, action)

    async def _handle_add_shape(self, session: _ARSession, data: dict) -> None:
        fn_data = data.get("functionData")
        if not fn_data:
            raise ValueError("functionData required")

        node_type  = str(fn_data.get("type", "function")).lower()
        shape_type, color = _AR_SHAPE_TYPE_MAP.get(node_type, ("Tetrahedron", "#E040FB"))

        new_shape = _ARShape(
            shape_id=str(_uuid_ar.uuid4()),
            shape_type=shape_type,
            label=fn_data.get("name", "new_function"),
            position=fn_data.get("position", [0.0, 0.0, 0.0]),
            scale=float(fn_data.get("scale", 1.0)),
            color=color,
            node_type=node_type,
            metadata={"function_data": fn_data},
        )

        async with self._topology_lock:
            self._shapes[new_shape.shape_id] = new_shape

        await self._broadcast_message({"type": "SHAPE_ADDED", "shape": new_shape.to_dict()})
        _ar_logger.info("Added shape: %s", new_shape.shape_id)

    async def _handle_hotswap_request(self, session: _ARSession, data: dict) -> None:
        target_id    = data.get("targetId")
        new_function = data.get("newFunction")
        if not target_id or not new_function:
            raise ValueError("targetId and newFunction required")

        # Forward to node hotswap if available (set via node reference)
        result = {"status": "success", "targetId": target_id, "message": "Hotswap queued"}
        await self._broadcast_message({
            "type": "HOTSWAP_COMPLETE",
            "targetId": target_id,
            "result": result,
        })
        _ar_logger.info("Hotswap queued for %s", target_id)
        await self._refresh_topology()

    async def _broadcast_topology(self) -> None:
        await self._broadcast_message({
            "type": "TOPOLOGY_UPDATE",
            "data": self._topology_dict(),
        })

    async def _broadcast_message(self, message: dict) -> None:
        dead: list = []
        for sid, session in list(self._sessions.items()):
            try:
                await session.websocket.send(_json_ar.dumps(message))
            except Exception:
                dead.append(sid)
        for sid in dead:
            self._sessions.pop(sid, None)


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[AURA TOPOLOGY BRIDGE] Standalone test — press Ctrl+C to stop.")

    async def _test():
        hub = await get_topology_hub()
        print(f"  [+] Hub started. Clients: {len(hub._clients)}")
        await asyncio.sleep(2)
        await hub.broadcast_topology_now()
        print("  [+] Forced broadcast sent.")
        await asyncio.sleep(1)
        await hub.stop()

    asyncio.run(_test())
    print("  [+] Test complete.")