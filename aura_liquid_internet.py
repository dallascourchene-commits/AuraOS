"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fd-[Q-SYS:LIQUID_INTERNET_PROTOCOL]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Non-Local Coupling)
DEPENDENCIES: numpy, hashlib, time, asyncio, json
FUNCTIONS: VSAAddress, PeerRecord, NameBinding, LiquidInternetProtocol
SYNOPSIS: VSA-Addressed Liquid Internet Protocol overlay (Claim N14). Every entity gets a 10,000-D phasor address. Routing by cosine resonance over TCP/IP transport. Decentralized naming via resonance search. Pure NumPy, no new dependencies.
[/AURA_MASTER_KEY]

VSA-Addressed Liquid Internet Protocol (Claim N14)
====================================================

An overlay protocol where:
  1. Every entity has a VSA phasor address (not an IP)
  2. Routing picks the highest-resonance neighbor (no routing tables)
  3. Names resolve by resonance search (no DNS)

The actual bytes still flow over TCP/IP. The VSA layer sits above it
as an addressing and routing overlay, same as Chord/Kademlia use hash
rings over TCP. The difference: cosine similarity in 10,000-D space
instead of XOR distance in 160-bit space.

Axiom A6: Non-Local Coupling. Distance is resonance, not topology.
Axiom A1: Every peer is a point in the 10,000-D field.
Axiom P4: Retrieval by resonance alignment, not traversal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import time
from typing import Any

import numpy as np

_DIM = 10000
_RESONANCE_ROUTE_FLOOR = 0.05
_NAME_RESONANCE_FLOOR = 0.3
_MAX_HOPS = 8
_ADDRESS_QUANTIZE_BYTES = 1200  # 1.2 KB quantized header


# ── Phasor codec (shared across all Aura modules) ──

def _seeded_phasor(label: str, dim: int = _DIM) -> np.ndarray:
    """Deterministic BLAKE2b-seeded complex phasor."""
    h = hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest()
    seed = int.from_bytes(h, byteorder="little")
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-np.pi, np.pi, dim).astype(np.float32)
    return np.exp(1j * phases)


def _cosine_res(a: np.ndarray, b: np.ndarray) -> float:
    """Complex cosine resonance (handles both unit-circle and normalized phasors)."""
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-12:
        return 0.0
    return float(np.abs(np.dot(a, np.conj(b))) / denom)


def _bind(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """VSA binding (element-wise complex multiply)."""
    return np.multiply(v1, v2)


def _bundle(*vectors: np.ndarray) -> np.ndarray:
    """VSA bundling (superposition + normalize)."""
    s = np.zeros(_DIM, dtype=np.complex64)
    for v in vectors:
        s += v
    norm = np.linalg.norm(s)
    if norm > 0:
        s /= norm
    return s


def _quantize_address(phasor: np.ndarray) -> bytes:
    """Quantize a 10,000-D phasor to 1.2 KB for transport."""
    q = np.clip(phasor.real * 127, -128, 127).astype(np.int8)
    return q.tobytes()[:_ADDRESS_QUANTIZE_BYTES]


def _dequantize_address(raw: bytes) -> np.ndarray:
    """Reconstruct phasor from quantized bytes."""
    arr = np.frombuffer(raw[:_ADDRESS_QUANTIZE_BYTES], dtype=np.int8)
    full = np.zeros(_DIM, dtype=np.float32)
    full[:len(arr)] = arr.astype(np.float32) / 127.0
    return full


# ── Data Structures ──

@dataclass
class VSAAddress:
    """A VSA phasor address for any entity."""
    phasor: np.ndarray         # 10,000-D complex unit phasor
    properties: dict[str, str] # semantic properties used to derive it
    quantized: bytes = b""     # 1.2 KB transport form

    @staticmethod
    def from_properties(properties: dict[str, str]) -> VSAAddress:
        """Generate address from semantic properties (Claim N14 Section 2.1).
        a_entity = normalize(bundle(v_prop_k bind role_k for k in properties))
        """
        bound_components = []
        for key, value in properties.items():
            v_prop = _seeded_phasor(value)
            role = _seeded_phasor(f"ROLE::{key}")
            bound_components.append(_bind(v_prop, role))

        if not bound_components:
            phasor = _seeded_phasor("EMPTY_ENTITY")
        else:
            phasor = _bundle(*bound_components)

        quantized = _quantize_address(phasor)
        return VSAAddress(phasor=phasor, properties=properties, quantized=quantized)

    @staticmethod
    def from_label(label: str) -> VSAAddress:
        """Quick address from a single label string."""
        return VSAAddress.from_properties({"identity": label})

    def resonance_with(self, other: VSAAddress) -> float:
        return _cosine_res(self.phasor, other.phasor)


@dataclass
class PeerRecord:
    """A peer in the VSA overlay network."""
    vsa_address: VSAAddress
    ip: str                    # underlying TCP/IP address (transport layer)
    port: int = 4445
    label: str = ""
    capabilities: list[str] = field(default_factory=list)
    last_seen: float = 0.0
    hop_count: int = 1


@dataclass
class NameBinding:
    """A name-to-address binding in the decentralized naming system."""
    name: str
    vsa_address: VSAAddress
    publisher_address: VSAAddress
    timestamp: float = 0.0
    signature: str = ""        # publisher signature (simplified)


# ── Liquid Internet Protocol ──

class LiquidInternetProtocol:
    """
    VSA-Addressed Liquid Internet Protocol (Claim N14).

    Overlay protocol where addressing and routing use 10,000-D
    phasor resonance, while actual transport uses TCP/IP underneath.

    Three operations:
      1. register_peer() - add a peer with its VSA address
      2. route() - find best next hop by resonance (no routing table)
      3. resolve_name() - resolve a human name to VSA address (no DNS)
    """

    def __init__(self, self_address: VSAAddress | None = None,
                 self_ip: str = "127.0.0.1", self_port: int = 4445):
        if self_address is None:
            self_address = VSAAddress.from_properties({
                "identity": self_ip,
                "type": "node",
                "entropy": hashlib.blake2b(
                    f"{self_ip}:{self_port}:{time.time()}".encode(), digest_size=8
                ).hexdigest(),
            })
        self.self_address = self_address
        self.self_ip = self_ip
        self.self_port = self_port

        # Peer registry: vsa_address_hash -> PeerRecord
        self._peers: dict[str, PeerRecord] = {}

        # Decentralized name bindings
        self._name_bindings: list[NameBinding] = []

    # ── Peer Management ──

    def register_peer(self, ip: str, port: int = 4445,
                      label: str = "", capabilities: list | None = None,
                      properties: dict | None = None) -> PeerRecord:
        """Register a peer with its VSA address derived from properties."""
        if properties is None:
            properties = {"identity": ip, "type": "node", "label": label}
        if capabilities:
            properties["capabilities"] = ",".join(capabilities)

        vsa_addr = VSAAddress.from_properties(properties)
        peer = PeerRecord(
            vsa_address=vsa_addr,
            ip=ip, port=port, label=label,
            capabilities=capabilities or [],
            last_seen=time.time(),
        )
        key = hashlib.md5(vsa_addr.quantized[:32]).hexdigest()
        self._peers[key] = peer
        return peer

    def register_peer_from_beacon(self, ip: str, label: str) -> PeerRecord:
        """Register a peer discovered via UDP beacon (bridge from aura_mesh)."""
        return self.register_peer(ip=ip, label=label,
                                  properties={"identity": ip, "label": label, "type": "node"})

    @property
    def peer_count(self) -> int:
        return len(self._peers)

    # ── Resonance Routing (Claim N14 Section 2.2) ──

    def route(self, destination: VSAAddress,
              max_hops: int = _MAX_HOPS) -> tuple[PeerRecord | None, dict]:
        """
        Route to a destination by resonance. No routing table.

        a_next = argmax_{a_i in N} cos(a_i, a_dest)

        Returns (best_peer, routing_report).
        """
        if not self._peers:
            return None, {"decision": "NO_PEERS", "peers_evaluated": 0}

        candidates = []
        for key, peer in self._peers.items():
            if peer.hop_count > max_hops:
                continue
            resonance = _cosine_res(peer.vsa_address.phasor, destination.phasor)
            if resonance >= _RESONANCE_ROUTE_FLOOR:
                candidates.append((resonance, peer))

        candidates.sort(key=lambda x: x[0], reverse=True)

        report = {
            "peers_evaluated": len(self._peers),
            "candidates_above_floor": len(candidates),
            "max_hops": max_hops,
            "resonance_floor": _RESONANCE_ROUTE_FLOOR,
        }

        if candidates:
            best_res, best_peer = candidates[0]
            report["decision"] = "ROUTE"
            report["next_hop_ip"] = best_peer.ip
            report["next_hop_port"] = best_peer.port
            report["next_hop_label"] = best_peer.label
            report["resonance"] = best_res
            report["alternative_count"] = len(candidates) - 1
            return best_peer, report
        else:
            report["decision"] = "NO_ROUTE"
            report["reason"] = "No peers above resonance floor within hop bound"
            return None, report

    def route_by_name(self, name: str,
                      max_hops: int = _MAX_HOPS) -> tuple[PeerRecord | None, dict]:
        """Route to a named entity: resolve name then route."""
        resolved = self.resolve_name(name)
        if resolved is None:
            return None, {"decision": "NAME_NOT_FOUND", "name": name}
        return self.route(resolved, max_hops=max_hops)

    # ── Decentralized Naming (Claim N14 Section 2.3) ──

    def publish_name(self, name: str, target_address: VSAAddress) -> NameBinding:
        """Publish a name binding (name -> VSA address)."""
        binding = NameBinding(
            name=name,
            vsa_address=target_address,
            publisher_address=self.self_address,
            timestamp=time.time(),
            signature=hashlib.blake2b(
                f"{name}:{time.time()}".encode(), digest_size=8
            ).hexdigest(),
        )
        self._name_bindings.append(binding)
        return binding

    def resolve_name(self, name: str) -> VSAAddress | None:
        """
        Resolve a human-readable name to a VSA address.
        Uses resonance search, not hierarchical DNS lookup.

        q_N = hash_to_phasor(name)
        result = argmax_{binding} cos(q_N, binding.vsa_address)
        """
        if not self._name_bindings:
            return None

        query_phasor = _seeded_phasor(name)
        best_res = -1.0
        best_addr = None

        for binding in self._name_bindings:
            # Check exact name match first (O(1))
            if binding.name == name:
                return binding.vsa_address

            # Resonance-based fuzzy resolution
            res = _cosine_res(query_phasor, binding.vsa_address.phasor)
            if res > best_res and res >= _NAME_RESONANCE_FLOOR:
                best_res = res
                best_addr = binding.vsa_address

        return best_addr

    def list_names(self) -> list[dict[str, Any]]:
        """List all published name bindings."""
        return [
            {"name": b.name, "timestamp": b.timestamp,
             "publisher_sig": b.signature[:16]}
            for b in self._name_bindings
        ]

    # ── Integration with aura_mesh.py ──

    def import_mesh_peers(self, mesh_peers: dict[str, str]) -> int:
        """Import peers from aura_mesh.py peer registry (ip -> label)."""
        count = 0
        for ip, label in mesh_peers.items():
            self.register_peer_from_beacon(ip, label)
            count += 1
        return count

    def get_routing_table_size(self) -> int:
        """Always returns 0. LIP has no routing table. That is the point."""
        return 0

    # ── Diagnostics ──

    def format_report(self) -> str:
        """Format protocol status report."""
        lines = [
            "[LIQUID_INTERNET_PROTOCOL]",
            f"SELF_IP: {self.self_ip}:{self.self_port}",
            f"PEERS: {self.peer_count}",
            f"NAME_BINDINGS: {len(self._name_bindings)}",
            f"ROUTING_TABLE_SIZE: {self.get_routing_table_size()} (by design)",
            f"ADDRESSING: vsa_phasor_{_DIM}d",
            "TRANSPORT: tcp/ip overlay",
        ]
        if self._peers:
            lines.append("PEER_REGISTRY:")
            for key, peer in list(self._peers.items())[:10]:
                lines.append(
                    f"  {peer.label or peer.ip}: "
                    f"res_to_self={_cosine_res(peer.vsa_address.phasor, self.self_address.phasor):.4f}"
                )
        lines.append("[/LIQUID_INTERNET_PROTOCOL]")
        return "\n".join(lines)


# ── CLI Demo ──

if __name__ == "__main__":
    print("=== VSA-Addressed Liquid Internet Protocol (N14) Demo ===\n")

    lip = LiquidInternetProtocol(self_ip="192.168.1.100")

    # Register peers with semantic properties
    lip.register_peer("192.168.1.101", label="aura_node_alpha",
                      capabilities=["compute", "memory", "research"],
                      properties={"identity": "alpha", "type": "node",
                                  "capabilities": "compute,memory,research"})
    lip.register_peer("192.168.1.102", label="aura_node_beta",
                      capabilities=["render", "topology", "ar"],
                      properties={"identity": "beta", "type": "node",
                                  "capabilities": "render,topology,ar"})
    lip.register_peer("10.0.0.50", label="aura_edge_gamma",
                      capabilities=["storage", "ledger"],
                      properties={"identity": "gamma", "type": "edge",
                                  "capabilities": "storage,ledger"})

    print(f"Registered {lip.peer_count} peers")
    print(f"Routing table size: {lip.get_routing_table_size()} (always zero)\n")

    # Route by semantic destination (not IP)
    dest = VSAAddress.from_properties({
        "type": "node", "capabilities": "compute,research"
    })
    peer, report = lip.route(dest)
    print("Route to 'compute+research' node:")
    print(f"  Decision: {report['decision']}")
    if peer:
        print(f"  Next hop: {peer.ip} ({peer.label})")
        print(f"  Resonance: {report.get('resonance', 0):.4f}\n")

    # Publish and resolve names (no DNS)
    lip.publish_name("alpha_compute", VSAAddress.from_label("alpha"))
    lip.publish_name("beta_render", VSAAddress.from_label("beta"))

    resolved = lip.resolve_name("alpha_compute")
    print(f"Resolve 'alpha_compute': {'FOUND' if resolved else 'NOT FOUND'}")

    peer2, report2 = lip.route_by_name("alpha_compute")
    print("Route by name 'alpha_compute':")
    print(f"  Decision: {report2.get('decision', 'NONE')}\n")

    print(lip.format_report())
    print("\nDemo complete.")
