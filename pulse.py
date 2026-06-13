"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f6-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, websockets, os, liquid_kernel, json
FUNCTIONS: bridge_handler, watch_memory, main, _get_files, _get_latest_st3
SYNOPSIS: The module implements an asynchronous WebSocket bridge using `asyncio` and `websockets`, integrating with `liquid_kernel` for memory management via `watch_memory`, while exposing a CLI via `main`, file operations via `_get_files`, and state tracking via `_get_latest_st3`, all with strict JSON serialization and OS-level path handling.
[/AURA_MASTER_KEY]
"""

import asyncio
import websockets
import json
import os
from liquid_kernel import LiquidWebSocket
from liquid_attractor_control_plane import auto_boot_attractor, shutdown_attractor

brain = LiquidWebSocket()
CONNECTED_CLIENTS = set()
MEMORY_DIR = "Aura_Memory"

# Attractor reference — set by main() on startup
_attractor = None


async def bridge_handler(websocket):
    global _attractor
    CONNECTED_CLIENTS.add(websocket)
    client_ip = websocket.remote_address[0]
    print(f"[+] AR Deck connected from {client_ip}.")

    # ── Wire this WebSocket client into the attractor broadcast plane ──
    client_q = asyncio.Queue(maxsize=32)
    if _attractor is not None:
        _attractor.graft_module("web_client", client_q)

    # Spawn a pump that forwards attractor frames to this WS client
    async def _attractor_pump():
        while True:
            try:
                payload = await asyncio.wait_for(client_q.get(), timeout=5.0)
                await websocket.send(payload)
            except asyncio.TimeoutError:
                continue
            except (websockets.exceptions.ConnectionClosed, Exception):
                break

    pump_task = asyncio.create_task(_attractor_pump())

    try:
        async for message in websocket:
            raw_payload = json.loads(message)
            
            # 1. Process through the Native Liquid Kernel
            processed_payload = await brain.process_command(raw_payload)
            
            # 2. ST3GG Stenography: Find the latest quantum memory (Offloaded to thread pool)
            def _get_latest_st3():
                if not os.path.exists(MEMORY_DIR):
                    return None
                try:
                    engrams = sorted([f for f in os.listdir(MEMORY_DIR) if f.endswith('.st3')])
                    return engrams[-1].replace('.st3', '') if engrams else None
                except Exception:
                    return None

            latest_engram = await asyncio.to_thread(_get_latest_st3)
            latest_st3gg = latest_engram if latest_engram is not None else "AWAITING_ENGRAM"
            
            # 3. Inject the hidden holographic stamp into the payload
            processed_payload["__st3gg__"] = latest_st3gg
            
            # Broadcast to the visual matrix
            if CONNECTED_CLIENTS:
                websockets.broadcast(CONNECTED_CLIENTS, json.dumps(processed_payload))
                
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass
        # Clean up attractor client queue
        if _attractor is not None:
            try:
                _attractor._web_clients = [q for q in _attractor._web_clients if q is not client_q]
            except Exception:
                pass
        print(f"[-] AR Deck disconnected.")

async def watch_memory():
    """Background loop: Watches for new DKT mutations and triggers AR Glyphs"""
    if not os.path.exists(MEMORY_DIR):
        return
        
    # Non-blocking initial dir load
    known_files = await asyncio.to_thread(lambda: set(os.listdir(MEMORY_DIR)))
    
    while True:
        await asyncio.sleep(1.0) # Check memory every second
        
        # Offload file scanning to prevent main thread event loop stalls
        def _get_files():
            try:
                return set(os.listdir(MEMORY_DIR))
            except Exception:
                return set()

        current_files = await asyncio.to_thread(_get_files)
        new_files = current_files - known_files
        
        for file in new_files:
            if file.endswith('.st3'):
                thought_id = file.replace('.st3', '')
                print(f"[*] Memory Watcher detected new engram: {thought_id}")
                
                # The payload that triggers the holographic stamp in your Chrome UI
                glyph_payload = {
                    "shape": "HolographicEngram", 
                    "lum": "MAX", 
                    "temp": "HOT",
                    "mutation_id": thought_id,
                    "status": "SYS_HEAL_COMPLETE"
                }
                
                if CONNECTED_CLIENTS:
                    websockets.broadcast(CONNECTED_CLIENTS, json.dumps(glyph_payload))
                    
        known_files = current_files

async def main():
    global _attractor
    print("=========================================")
    print(" 🌐 AURA SOVEREIGN MESH BRIDGE ONLINE 🌐 ")
    print("=========================================")

    # ── Auto-boot the Liquid Spatiotemporal Attractor control plane ──
    try:
        _attractor = await auto_boot_attractor(
            mesh_swarm=None,   # aura_mesh swarms wire themselves separately
            ar_server=None,    # AR server optional
            unreal_bridge=None,
        )
    except Exception as e:
        print(f"[-] [PULSE] Attractor auto-boot failed: {e} — continuing without control plane.")

    # Corrected: Guard port binding with exception-handling to absorb address conflict panics
    try:
        async with websockets.serve(bridge_handler, "0.0.0.0", 8081):
            print("[+] AURA SOVEREIGN MESH BRIDGE bound to Port 8081.")
            await asyncio.gather(
                watch_memory(),
                asyncio.Future()  # Standby forever
            )
    except Exception as e:
        print(f"[-] [PULSE] Server bind failed on Port 8081: {e}. Moving to standby mode.")
        while True:
            await asyncio.sleep(3600)  # Idle standby prevents thread exit
    finally:
        # Graceful shutdown
        await shutdown_attractor()

if __name__ == "__main__":
    asyncio.run(main())
