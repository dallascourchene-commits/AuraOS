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