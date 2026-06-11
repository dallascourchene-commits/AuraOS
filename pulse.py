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

brain = LiquidWebSocket()
CONNECTED_CLIENTS = set()
MEMORY_DIR = "Aura_Memory"

async def bridge_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    client_ip = websocket.remote_address[0]
    print(f"[+] AR Deck connected from {client_ip}.")

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
    print("=========================================")
    print(" 🌐 AURA SOVEREIGN MESH BRIDGE ONLINE 🌐 ")
    print("=========================================")
    
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

if __name__ == "__main__":
    asyncio.run(main())
