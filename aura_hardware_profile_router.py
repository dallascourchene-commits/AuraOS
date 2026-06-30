"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:HARDWARE_PROFILE_ROUTER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Hardware Mapping)
DEPENDENCIES: __future__, typing, aura_scene_graph_schema
FUNCTIONS: AuraHardwareProfileRouter, assign_profile_to_node, probe_capabilities
SYNOPSIS: Evaluates host hardware capabilities and issues advisory device recommendations.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from typing import Dict, Any
from aura_scene_graph_schema import HardwareProfile, AURA_HARDWARE_PROFILE_V1


class AuraHardwareProfileRouter:
    """
    Profiles processing requirements and issues advisory recommendations for CPU/GPU/NPU/AIE targets.
    Probes host system capabilities deterministically to keep recommendations honest.
    """

    @staticmethod
    def probe_capabilities() -> Dict[str, Any]:
        """Probes host hardware capabilities (ROCm, Ryzen AI, threads, memory)."""
        import os
        import platform
        import multiprocessing

        cpu_threads = multiprocessing.cpu_count()
        rocm_available = False
        npu_backend_available = False
        gpu_memory_mb = 0

        # Simple heuristics for capability detection
        system = platform.system().lower()
        if system == "linux":
            # Check for ROCm library paths
            if os.path.exists("/opt/rocm") or os.path.exists("/dev/kfd"):
                rocm_available = True
            # Check for Ryzen AI / XDNA NPU driver node
            if os.path.exists("/sys/class/accel") or os.path.exists("/dev/amdxdna"):
                npu_backend_available = True
        elif system == "windows":
            # Heuristic for Windows driver check
            try:
                # Check environment variables or subprocess for Ryzen AI/ROCm
                if "rocm" in os.environ.get("PATH", "").lower():
                    rocm_available = True
            except Exception:
                pass

        available_devices = ["CPU"]
        if rocm_available:
            available_devices.append("GPU")
            gpu_memory_mb = 8192  # Default baseline for ROCm compatible card in demo
        if npu_backend_available:
            available_devices.append("NPU")

        return {
            "available_devices": available_devices,
            "rocm_available": rocm_available,
            "npu_backend_available": npu_backend_available,
            "gpu_memory_mb": gpu_memory_mb,
            "cpu_threads": cpu_threads,
        }

    @classmethod
    def assign_profile_to_node(cls, node_type: str, complex_matrix_operations: bool) -> HardwareProfile:
        """Emits advisory hardware recommendations for a given node type."""
        caps = cls.probe_capabilities()
        
        if node_type in ("verifier", "contract"):
            # Control flow verification -> CPU
            return HardwareProfile(
                operational_intensity=0.15,
                capacity_footprint_mb=4.2,
                memory_bandwidth_pressure=0.08,
                latency_sensitivity=0.9,
                kv_cache_reuse_score=1.0,
                parallelism_score=0.1,
                preferred_device="CPU",
                reason="Verification checks require single-thread CPU precision.",
                execution_status="executed" if "CPU" in caps["available_devices"] else "recommended"
            )

        if node_type == "symbol" and complex_matrix_operations:
            # VSA/DREAM scoring -> NPU/GPU recommended
            npu_available = caps["npu_backend_available"]
            preferred = "NPU" if npu_available else "GPU" if caps["rocm_available"] else "CPU"
            status = "executed" if preferred in caps["available_devices"] else "recommended"
            reason = "High-intensity matrix operations. "
            if preferred == "NPU":
                reason += "Recommended for Ryzen AI / XDNA-family NPU when a backend is available."
            elif preferred == "GPU":
                reason += "Offloaded to ROCm GPU path."
            else:
                reason += "No local accelerator backend detected; running on CPU."

            return HardwareProfile(
                operational_intensity=85.4,
                capacity_footprint_mb=512.0,
                memory_bandwidth_pressure=0.72,
                latency_sensitivity=0.4,
                kv_cache_reuse_score=0.65,
                parallelism_score=0.9,
                preferred_device=preferred,
                reason=reason,
                execution_status=status
            )

        # Default profile
        return HardwareProfile(
            operational_intensity=1.2,
            capacity_footprint_mb=16.0,
            memory_bandwidth_pressure=0.20,
            latency_sensitivity=0.5,
            kv_cache_reuse_score=0.80,
            parallelism_score=0.5,
            preferred_device="CPU",
            reason="Standard execution path.",
            execution_status="executed"
        )
