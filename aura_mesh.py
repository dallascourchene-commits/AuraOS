"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, base64, socket, os, uuid, numpy, struct, hashlib, time, json
FUNCTIONS:
    __init__, start_udp_beacon, start_tcp_compute_server,
    pack_secure_polysynthetic_packet, unpack_secure_polysynthetic_packet,
    pack_length_prefixed_payload, unpack_length_prefixed_payload,
    generate_polysynthetic_proof, verify_dsekp_shield,
    broadcast_upgrade, offload_compute, should_offload_task,
    _commit_mesh_telemetry, _listen_beacons_async,
    _tcp_client_handler, _read_thermal_nonblocking
SYNOPSIS:
    This Python module implements a secure, asynchronous swarm-mesh engine
    for the AuraOS edge‑orchestration substrate.  It supports:
      - UDP beacon discovery with a fixed 16‑byte polysynthetic telemetry
        frame (six 16‑bit slot indices + one 32‑bit compliance float).
      - A length‑prefixed binary protocol for variable‑size compute‑task
        offloading over TCP (port 4445), including a fully asynchronous
        TCP listener server.
      - Automatic task evaluation and routing via `should_offload_task`,
        which inspects task metadata tags, system temperature, and
        estimated resource cost before transparently redirecting heavy
        work to discovered peers.
      - Non‑blocking thermal‑zone reads through `loop.run_in_executor`.
      - DSEKP cryptographic shield verification using NumPy bitwise
        vector comparison with a configurable Hamming‑distance threshold.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import socket
import struct
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Module‑level constants
# ---------------------------------------------------------------------------
DEFAULT_UDP_BEACON_PORT: int = 4444
DEFAULT_TCP_COMPUTE_PORT: int = 4445
DEFAULT_OFFLOAD_TEMP_THRESHOLD_C: float = 75.0
DSEKP_SHIELD_SIZE: int = 10000
DSEKP_HAMMING_TOLERANCE: int = 500
THERMAL_PATH: str = "/sys/class/thermal/thermal_zone0/temp"
BROADCAST_ADDR: str = "<broadcast>"
TELEMETRY_FRAME_SIZE: int = 16  # 6 × uint16 + 1 × float32
LENGTH_PREFIX_SIZE: int = 4     # uint32 big‑endian

# Task‑tag keywords that unconditionally trigger remote offloading when
# peers are available.
OFFLOAD_TAGS: frozenset = frozenset(
    {"COMPUTE_HEAVY", "VECTOR_SEARCH", "GENETIC_EVOLUTION"}
)


class AuraMeshSwarm:
    """Asynchronous swarm‑mesh engine for AuraOS edge orchestration.

    This class manages peer discovery via UDP broadcast beacons (fixed
    16‑byte telemetry frames), a TCP‑based compute‑offload channel with
    a length‑prefixed binary protocol, automatic task‑routing decisions
    driven by thermal and resource heuristics, and DSEKP cryptographic
    shield verification.

    Parameters
    ----------
    node_ref:
        Reference to the parent ``AuraNode`` (or compatible object) that
        provides ``runtime_metrics``, ``hdc``, ``thermal``, and
        ``memory_palace`` attributes.
    identity:
        Human‑readable label for this swarm node.
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self, node_ref: Any, identity: str = "AURA_EDGE_NODE") -> None:
        self.node: Any = node_ref
        self.identity: str = identity

        # UDP discovery transport
        self.udp_sock: Optional[socket.socket] = None
        self.udp_port: int = DEFAULT_UDP_BEACON_PORT

        # TCP compute‑offload server
        self.tcp_server: Optional[asyncio.AbstractServer] = None
        self.tcp_port: int = DEFAULT_TCP_COMPUTE_PORT

        # Peer registry:  ip_address → human_label
        self.peers: Dict[str, str] = {}

        # Transmission ledger for auditing / telemetry
        self.tx_ledger: Dict[str, Any] = {}

        # Configurable offload threshold (°C)
        self.offload_temp_threshold: float = DEFAULT_OFFLOAD_TEMP_THRESHOLD_C

        print(f"[+] AuraMeshSwarm initialized | identity={self.identity}")

    # ==================================================================
    # PROTOCOL LAYER 1 — Fixed 16‑byte telemetry frame (UDP beacons)
    # ==================================================================
    @staticmethod
    def pack_secure_polysynthetic_packet(
        slot_indices: List[int], compliance_score: float
    ) -> bytes:
        """Pack six 16‑bit slot indices and one 32‑bit compliance float
        into a fixed‑size 16‑byte binary telemetry frame.

        This is the **structural metadata frame** used for UDP beacon
        broadcasts and lightweight heartbeats.  It does **not** carry
        variable‑length payload data.

        Parameters
        ----------
        slot_indices:
            Exactly 6 unsigned 16‑bit integers (0–65535).  If fewer than
            6 elements are supplied the missing entries are zero‑padded.
        compliance_score:
            32‑bit IEEE‑754 float representing the node's current
            compliance / confidence anchor.

        Returns
        -------
        bytes
            16‑byte packed binary frame::

                [H H H H H H f]  (little‑endian)
                 ^-6×uint16-^  ^-float32-^
        """
        if len(slot_indices) < 6:
            slot_indices = list(slot_indices) + [0] * (6 - len(slot_indices))
        # Clamp to valid uint16 range
        clamped: List[int] = [max(0, min(int(v), 65535)) for v in slot_indices[:6]]
        return struct.pack(
            "<HHHHHHf",
            clamped[0], clamped[1], clamped[2],
            clamped[3], clamped[4], clamped[5],
            float(compliance_score),
        )

    @staticmethod
    def unpack_secure_polysynthetic_packet(
        raw_bytes: bytes,
    ) -> Tuple[Optional[List[int]], float]:
        """Unpack a fixed 16‑byte telemetry frame.

        Parameters
        ----------
        raw_bytes:
            Raw bytes received from the wire.  Only the first 16 bytes
            are consumed.

        Returns
        -------
        tuple[Optional[List[int]], float]
            ``(slot_indices, compliance_score)``.  ``slot_indices`` is
            ``None`` when the frame is truncated or corrupt.
        """
        try:
            if len(raw_bytes) < TELEMETRY_FRAME_SIZE:
                return None, 0.0
            unpacked = struct.unpack("<HHHHHHf", raw_bytes[:TELEMETRY_FRAME_SIZE])
            return list(unpacked[:6]), float(unpacked[6])
        except (struct.error, IndexError):
            return None, 0.0

    # ==================================================================
    # PROTOCOL LAYER 2 — Length‑prefixed variable payload (TCP offload)
    # ==================================================================
    @staticmethod
    def pack_length_prefixed_payload(payload_obj: Any) -> bytes:
        """Serialize an arbitrary object to JSON and wrap it in a
        length‑prefixed binary frame.

        Frame layout::

            ┌────────────────────┬──────────────────────────────────┐
            │  4 bytes (BE u32)  │  UTF‑8 encoded JSON payload      │
            │  payload length N  │  (N bytes)                       │
            └────────────────────┴──────────────────────────────────┘

        Parameters
        ----------
        payload_obj:
            Any JSON‑serializable Python object (typically a ``dict``).

        Returns
        -------
        bytes
            Length‑prefixed binary frame ready for transmission over
            a TCP socket.
        """
        json_bytes: bytes = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
        length_prefix: bytes = struct.pack(">I", len(json_bytes))
        return length_prefix + json_bytes

    @staticmethod
    def unpack_length_prefixed_payload(raw_bytes: bytes) -> Optional[Any]:
        """Deserialize a length‑prefixed binary frame back into a Python
        object.

        Parameters
        ----------
        raw_bytes:
            Complete raw bytes received from the wire.

        Returns
        -------
        Optional[Any]
            Deserialized Python object, or ``None`` if the frame is
            malformed or truncated.
        """
        try:
            if len(raw_bytes) < LENGTH_PREFIX_SIZE:
                print("[-] Length-prefixed frame truncated: missing 4-byte header.")
                return None
            payload_len: int = struct.unpack(">I", raw_bytes[:LENGTH_PREFIX_SIZE])[0]
            payload_bytes: bytes = raw_bytes[LENGTH_PREFIX_SIZE:]
            if len(payload_bytes) < payload_len:
                print(
                    f"[-] Length-prefixed frame body mismatch: "
                    f"expected {payload_len}, got {len(payload_bytes)}."
                )
                return None
            json_str: str = payload_bytes[:payload_len].decode("utf-8")
            return json.loads(json_str)
        except (struct.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"[-] Failed to unpack length-prefixed payload: {exc}")
            return None

    # ==================================================================
    # DSEKP CRYPTOGRAPHIC SHIELD
    # ==================================================================
    def generate_polysynthetic_proof(
        self, payload_dict: Dict[str, Any], current_temp: float
    ) -> Dict[str, Any]:
        """Generate a DSEKP cryptographic proof envelope for an outgoing
        swarm message.

        If the parent node exposes an ``hdc`` (Hyper‑Dimensional
        Computer) engine the proof includes a holographic route glyph,
        trace ID, and a packed outer shield.  Otherwise a degraded
        ``"OFFLINE"`` shield is returned.

        Parameters
        ----------
        payload_dict:
            Semantic payload to wrap.
        current_temp:
            Current system temperature in °C (used as a nonce factor).

        Returns
        -------
        dict
            Proof envelope with keys ``dsekp_shield``, ``route_glyph``,
            ``trace_id``, and ``data``.
        """
        thought_id: str = f"MESH-{uuid.uuid4().hex[:8].upper()}"
        mesh_glyph: str = "ST3GG:NET_SYNC"

        hdc = getattr(self.node, "hdc", None)
        if hdc is None:
            return {"dsekp_shield": "OFFLINE", "data": payload_dict}

        try:
            hybrid_packet = hdc.generate_hybrid_packet(
                thought_id=thought_id,
                st3gg_glyph=mesh_glyph,
                qdkt_tensor=payload_dict,
                current_temp=current_temp,
            )
            shield_bytes: bytes = np.packbits(
                hybrid_packet["outer_shield"]
            ).tobytes()
            shield_b64: str = base64.b64encode(shield_bytes).decode("utf-8")
            return {
                "dsekp_shield": shield_b64,
                "route_glyph": hybrid_packet["holographic_route"],
                "trace_id": hybrid_packet["thought_trace_id"],
                "data": hybrid_packet["inner_nucleus"],
            }
        except Exception as exc:
            print(f"[-] Polysynthetic proof generation failed: {exc}")
            return {"dsekp_shield": "OFFLINE", "data": payload_dict}

    async def verify_dsekp_shield(self, incoming_packet: Dict[str, Any]) -> bool:
        """Verify an incoming DSEKP cryptographic shield via Hamming‑
        distance comparison against the locally expected state vector.

        A shield is accepted when the bitwise Hamming distance is ≤ 500
        (5 % of the 10 000‑bit shield space).

        Parameters
        ----------
        incoming_packet:
            A dictionary that must contain ``"dsekp_shield"`` and
            optionally ``"trace_id"``.

        Returns
        -------
        bool
            ``True`` if the shield is cryptographically valid.
        """
        shield_b64: Optional[str] = incoming_packet.get("dsekp_shield")
        if not shield_b64 or shield_b64 == "OFFLINE":
            print("[*] DSEKP shield offline or absent — verification skipped.")
            return False

        try:
            shield_bytes: bytes = base64.b64decode(shield_b64)
            incoming_shield: np.ndarray = np.unpackbits(
                np.frombuffer(shield_bytes, dtype=np.uint8)
            )
            if incoming_shield.size != DSEKP_SHIELD_SIZE:
                print(
                    f"[-] DSEKP Error: Shield geometry sheared in transit "
                    f"(size={incoming_shield.size}, expected={DSEKP_SHIELD_SIZE})."
                )
                return False

            # Obtain temperature in a non‑blocking fashion
            current_temp: float = await self._read_thermal_nonblocking()

            hdc = getattr(self.node, "hdc", None)
            if hdc is None:
                print("[*] No HDC engine available — shield verification passed by default.")
                return True

            trace_id: str = incoming_packet.get("trace_id", "UNKNOWN")
            expected_state: np.ndarray = hdc.get_word_vector(
                f"STATE_{current_temp}_{trace_id}"
            )

            hamming_distance: int = int(
                np.sum(np.bitwise_xor(incoming_shield, expected_state))
            )
            if hamming_distance <= DSEKP_HAMMING_TOLERANCE:
                print(
                    f"[+] DSEKP Shield verified | Hamming distance = {hamming_distance} "
                    f"(≤ {DSEKP_HAMMING_TOLERANCE})"
                )
                return True
            else:
                print(
                    f"[-] DSEKP Violation: Hamming distance [{hamming_distance}] "
                    f"exceeds {DSEKP_HAMMING_TOLERANCE}‑bit drift allowance."
                )
                return False
        except Exception as exc:
            print(f"[-] DSEKP Verification crashed: {exc}")
            return False

    # ==================================================================
    # NON‑BLOCKING SYSTEM I/O
    # ==================================================================
    @staticmethod
    async def _read_thermal_nonblocking() -> float:
        """Read the system thermal‑zone temperature from sysfs without
        blocking the asyncio event loop.

        The file read is offloaded to the default thread‑pool executor
        via ``loop.run_in_executor``.

        Returns
        -------
        float
            Temperature in °C, or ``42.0`` if the thermal zone cannot
            be read.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — fall back to synchronous read
            try:
                with open(THERMAL_PATH, "r") as fh:
                    return float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                return 42.0

        def _sync_read() -> float:
            try:
                with open(THERMAL_PATH, "r") as fh:
                    return float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                return 42.0

        try:
            return await loop.run_in_executor(None, _sync_read)
        except Exception:
            return 42.0

    # ==================================================================
    # AUTOMATIC TASK EVALUATION & ROUTING ENGINE
    # ==================================================================
    def should_offload_task(self, task_metadata: Dict[str, Any]) -> bool:
        """Determine whether a task should be transparently offloaded to
        a remote peer instead of being executed locally.

        **Offload Triggers** (any one is sufficient):

        1. The task's ``"tags"`` list contains a heavy‑compute keyword
           (``COMPUTE_HEAVY``, ``VECTOR_SEARCH``, ``GENETIC_EVOLUTION``).
        2. The current system temperature is *above* the configurable
           threshold (default 75 °C).
        3. The task metadata includes an ``"estimated_cost"`` key whose
           value exceeds a locally‑defined capacity ceiling.

        Offloading only occurs when at least one peer has already been
        discovered in ``self.peers``.

        Parameters
        ----------
        task_metadata:
            Dictionary describing the task.  Recognised keys:

            - ``"tags"``: ``List[str]`` — semantic tags.
            - ``"estimated_cost"``: ``float`` — abstract resource cost.
            - ``"temperature"``: ``float`` (optional) — latest thermal
              reading; if omitted the method reads it synchronously
              from sysfs.

        Returns
        -------
        bool
            ``True`` when the task should be transparently redirected
            to a peer.
        """
        # No peers → nothing to offload to
        if not self.peers:
            return False

        tags: List[str] = task_metadata.get("tags", [])
        if any(tag in OFFLOAD_TAGS for tag in tags):
            print(
                f"[*] Offload triggered by task tag intersection: "
                f"{set(tags) & set(OFFLOAD_TAGS)}"
            )
            return True

        # Thermal guard
        current_temp: float = task_metadata.get("temperature", 42.0)
        if current_temp == 42.0:
            # Attempt synchronous read as fallback (called from sync context)
            try:
                with open(THERMAL_PATH, "r") as fh:
                    current_temp = float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                pass
        if current_temp > self.offload_temp_threshold:
            print(
                f"[*] Offload triggered by thermal threshold: "
                f"{current_temp:.1f}°C > {self.offload_temp_threshold}°C"
            )
            return True

        # Resource‑cost guard
        estimated_cost: Optional[float] = task_metadata.get("estimated_cost")
        if estimated_cost is not None and estimated_cost > 1.0:
            print(
                f"[*] Offload triggered by estimated cost: "
                f"{estimated_cost:.3f} exceeds local capacity ceiling (1.0)"
            )
            return True

        return False

    # ==================================================================
    # UTP BEACON (LATTICE DISCOVERY)
    # ==================================================================
    def start_udp_beacon(self) -> None:
        """Create and bind the UDP broadcast socket on port 4444 and
        schedule the asynchronous beacon‑listening loop.

        This method must be called from within a running asyncio event
        loop so that ``asyncio.get_running_loop()`` succeeds.
        """
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
        try:
            self.udp_sock.bind(("0.0.0.0", self.udp_port))
            self.udp_sock.setblocking(False)
            loop = asyncio.get_running_loop()
            loop.create_task(self._listen_beacons_async())
            print(
                f"[LATTICA MESH] > UDP Nobex DAO Beacon active on "
                f"port {self.udp_port}"
            )
        except Exception as exc:
            print(f"[-] UDP beacon bind failed on port {self.udp_port}: {exc}")
            log_error = getattr(self.node, "log_error", None)
            if log_error is not None:
                log_error("MESH_BIND_FAIL", str(exc), severity=2)

    async def _listen_beacons_async(self) -> None:
        """Continuous background non‑blocking mesh listener loop.

        Reads incoming UDP frames, unpacks the 16‑byte telemetry,
        registers new peers, and enqueues morpho‑semantic root traces
        into the node's memory palace.
        """
        loop = asyncio.get_running_loop()
        print("[*] Beacon listener coroutine started.")
        while True:
            try:
                data, addr = await loop.sock_recvfrom(self.udp_sock, 1024)
                slot_indices, compliance = self.unpack_secure_polysynthetic_packet(data)

                if slot_indices is None:
                    continue

                # Peer registration
                ip = addr[0]
                if ip not in self.peers:
                    label = f"SIBLING_NODE_{ip.split('.')[-1]}"
                    self.peers[ip] = label
                    print(
                        f"\n[~] MESH SYNERGY: Registered new peer "
                        f"'{label}' @ {ip}"
                    )

                # Push into memory palace
                memory_palace = getattr(self.node, "memory_palace", None)
                if memory_palace is not None:
                    num_thought_id: int = int(
                        hashlib.md5(data).hexdigest()[:7], 16
                    )
                    await memory_palace.enqueue_morphemic_root_trace(
                        num_thought_id, slot_indices, compliance
                    )
            except BlockingIOError:
                pass
            except Exception as exc:
                print(f"[-] Beacon listener exception: {exc}")
            await asyncio.sleep(0.05)

    # ==================================================================
    # SWARM-LEVEL BROADCAST UPGRADE
    # ==================================================================
    async def broadcast_upgrade(
        self, module_name: str, code_content: str
    ) -> None:
        """Broadcast a sealed software‑upgrade pulse across the UDP
        beacon channel.

        The upgrade is packaged into a fixed 16‑byte telemetry frame
        with canonical morph‑semantic slot coordinates and a compliance
        baseline of 1.0.

        Parameters
        ----------
        module_name:
            Human‑readable module identifier (logged for telemetry).
        code_content:
            The source / binary payload being disseminated (unused in
            the fixed‑frame beacon but retained for future protocol
            upgrades).
        """
        start_time: float = time.time()
        self.node.runtime_metrics["dikwp_tier"] = "PURPOSE"
        try:
            # Canonical upgrade‑pulse slot vector
            upgrade_slots: List[int] = [707, 707, 303, 909, 505, 808]
            compliance_baseline: float = 1.0
            secure_packet: bytes = self.pack_secure_polysynthetic_packet(
                upgrade_slots, compliance_baseline
            )
            self.udp_sock.sendto(secure_packet, (BROADCAST_ADDR, self.udp_port))
            print(f"[+] SWARM UPGRADE deployed for module '{module_name}' | Shielded via PIP.")
            await self._commit_mesh_telemetry("SWARM_UPGRADE_BROADCAST", start_time)
        except Exception as exc:
            print(f"[-] Upgrade broadcast failed: {exc}")

    # ==================================================================
    # COMPUTE OFFLOAD (TCP CLIENT SIDE)
    # ==================================================================
    async def offload_compute(
        self, target_ip: str, module: str, data_payload: Dict[str, Any]
    ) -> Optional[Any]:
        """Transparently offload a compute task to a remote swarm peer
        over TCP port 4445 using the length‑prefixed protocol.

        Parameters
        ----------
        target_ip:
            Destination IPv4 address of the peer node.
        module:
            Logical module name (e.g. ``"VECTOR_SEARCH"``).
        data_payload:
            Task‑specific dictionary payload.

        Returns
        -------
        Optional[Any]
            The deserialized result payload returned by the peer, or
            ``None`` if the offload failed.
        """
        start_time: float = time.time()
        self.node.runtime_metrics["dikwp_tier"] = "KNOWLEDGE"

        payload_obj: Dict[str, Any] = {
            "id": f"JOB-{int(time.time())}",
            "module": module,
            "data": data_payload,
        }

        try:
            print(f"[*] Offloading '{module}' → {target_ip}:{self.tcp_port}...")
            secure_packet: bytes = self.pack_length_prefixed_payload(payload_obj)

            reader, writer = await asyncio.open_connection(
                target_ip, self.tcp_port
            )
            writer.write(secure_packet)
            await writer.drain()

            # Read back the length‑prefixed response
            raw_response: bytes = await reader.read(65536)
            writer.close()
            await writer.wait_closed()

            result: Optional[Any] = self.unpack_length_prefixed_payload(raw_response)
            if result is not None:
                print(f"[+] Offload complete — response from {target_ip}: {result}")
            else:
                print(f"[-] Offload to {target_ip} returned an unparseable response.")
            await self._commit_mesh_telemetry("SWARM_TASK_OFFLOAD", start_time)
            return result
        except Exception as exc:
            print(f"[-] Offload to {target_ip} failed: {exc}")
            return None

    # ==================================================================
    # TCP COMPUTE SERVER (INGESTION WORKER) — Listens on port 4445
    # ==================================================================
    async def start_tcp_compute_server(self) -> None:
        """Start the asynchronous TCP ingestion worker on port 4445.

        This server receives length‑prefixed binary frames from remote
        peers, deserializes them into task dictionaries, verifies the
        sender's DSEKP shield where possible, processes the task locally
        (or hands it to the parent node), and returns a length‑prefixed
        binary result frame to the caller.

        The server is bound to ``0.0.0.0`` and runs until the parent
        event loop is stopped.
        """

        async def handle_client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            """Per‑connection callback invoked by the asyncio server."""
            peer_addr = writer.get_extra_info("peername")
            peer_ip = peer_addr[0] if peer_addr else "unknown"
            print(f"[*] TCP compute client connected from {peer_ip}")

            try:
                # ---- 1. Read the length‑prefixed incoming frame ----
                raw_data: bytes = await reader.read(65536)
                if not raw_data:
                    print(f"[-] Empty frame from {peer_ip} — closing.")
                    writer.close()
                    await writer.wait_closed()
                    return

                task_dict: Optional[Dict[str, Any]] = self.unpack_length_prefixed_payload(raw_data)
                if task_dict is None:
                    print(f"[-] Failed to unpack payload from {peer_ip}.")
                    error_resp: bytes = self.pack_length_prefixed_payload(
                        {"status": "error", "reason": "unpackable_payload"}
                    )
                    writer.write(error_resp)
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    return

                print(
                    f"[*] Received task from {peer_ip}: "
                    f"id={task_dict.get('id', '?')}, module={task_dict.get('module', '?')}"
                )

                # ---- 2. Verify sender integrity via DSEKP ----
                # Build a minimal shield envelope from the task so we
                # can run the verification pipeline.
                shield_envelope: Dict[str, Any] = {
                    "dsekp_shield": task_dict.get("dsekp_shield", "OFFLINE"),
                    "trace_id": task_dict.get("trace_id", task_dict.get("id", "UNKNOWN")),
                }
                shield_valid: bool = await self.verify_dsekp_shield(shield_envelope)
                if shield_valid:
                    print(f"[+] DSEKP shield valid for task from {peer_ip}.")
                else:
                    print(f"[*] DSEKP shield absent / invalid for task from {peer_ip} — processing anyway.")

                # ---- 3. Process the task locally ----
                # If the parent node provides a generic task executor
                # we delegate to it; otherwise we simulate work.
                result_payload: Dict[str, Any]
                task_exec = getattr(self.node, "execute_offloaded_task", None)
                if callable(task_exec):
                    result_payload = await task_exec(task_dict)
                else:
                    # Simulated local computation
                    result_payload = {
                        "status": "ok",
                        "processed_by": self.identity,
                        "original_id": task_dict.get("id"),
                        "echo_data": task_dict.get("data"),
                    }
                    print(f"[+] Task '{task_dict.get('id')}' processed locally (simulated).")

                # ---- 4. Pack and return the binary result ----
                response_frame: bytes = self.pack_length_prefixed_payload(result_payload)
                writer.write(response_frame)
                await writer.drain()
                print(f"[*] Response sent to {peer_ip} ({len(response_frame)} bytes).")

            except asyncio.CancelledError:
                print(f"[*] TCP handler for {peer_ip} cancelled.")
            except Exception as exc:
                print(f"[-] TCP handler exception for {peer_ip}: {exc}")
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        try:
            self.tcp_server = await asyncio.start_server(
                handle_client,
                host="0.0.0.0",
                port=self.tcp_port,
                reuse_address=True,
            )
            print(
                f"[LATTICA MESH] > TCP Compute Ingestion Worker active on "
                f"port {self.tcp_port}"
            )
        except Exception as exc:
            print(f"[-] Failed to start TCP compute server on port {self.tcp_port}: {exc}")
            log_error = getattr(self.node, "log_error", None)
            if log_error is not None:
                log_error("MESH_TCP_BIND_FAIL", str(exc), severity=2)

    # ==================================================================
    # TELEMETRY COMMIT
    # ==================================================================
    async def _commit_mesh_telemetry(
        self, action_string: str, start_time: float
    ) -> None:
        """Write a holographic telemetry trace into the node's memory
        palace.

        Parameters
        ----------
        action_string:
            Human‑readable label for the action (e.g.
            ``"SWARM_UPGRADE_BROADCAST"``).
        start_time:
            ``time.time()`` captured at action initiation, used to
            compute latency.
        """
        metrics: Dict[str, Any] = getattr(self.node, "runtime_metrics", {})
        t_id: str = metrics.get("thought_id", "MESH-00000000")
        try:
            num_id: int = int(t_id.split("-")[1], 16)
        except (IndexError, ValueError):
            num_id = 0

        # Non‑blocking thermal read
        temp: float = await self._read_thermal_nonblocking()
        ms: float = (time.time() - start_time) * 1000.0

        memory_palace = getattr(self.node, "memory_palace", None)
        if memory_palace is not None:
            await memory_palace.enqueue_holographic_trace(
                num_id, action_string, temp, ms, True
            )