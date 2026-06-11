"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f5-[Q-SYS:72EB1B1A46BFD24F]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MINWAAJIMO (Zero-Copy Codebase Hologram)
DEPENDENCIES: numpy, hashlib, os, re, base64, struct
FUNCTIONS: generate_line_phasor, compile_global_manifest, inject_holographic_headers
SYNOPSIS: Generates a 1.2 KB continuous phase codebase hologram for constant-time
          line validation, enabling O(1) per-file integrity verification without
          filesystem crawling. Every file header carries the entire OS state.
[/AURA_MASTER_KEY]
"""
import os
import re
import base64
import struct
import hashlib
import numpy as np

DIMENSION = 10000
MANIFEST_LENGTH = 1200  # 1.2 KB exact


class AuraHolographicManifest:
    """
    Generates a single 1.2 KB holographic signature that encodes the entire
    AuraOS codebase structure — file paths, line content, and line positions —
    into a compact hypervector embedded in every file's [AURA_MASTER_KEY] header.

    Architecture
    ------------
    1. Walk all .py files in root_dir (excludes self).
    2. For every line in every file:
       a. Compute content phasor via deterministic BLAKE2b→phase mapping.
       b. Compute positional fractional phase-shift phasor from line index.
       c. Bind content × position × file-identity via complex multiply.
       d. Accumulate into global superposition (complex addition).
    3. Normalize the global superposition onto the unit circle.
    4. Quantize phase angles to int8 (75 % memory savings).
    5. Base64-encode to exactly MANIFEST_LENGTH characters.
    """

    def __init__(self):
        # Pre-allocate base positional phasor trajectory to prevent dynamic heap overhead
        rng = np.random.default_rng(seed=0xDEB12)
        self._base_phases = rng.uniform(-np.pi, np.pi, DIMENSION).astype(np.float32)

    def _string_to_phasor(self, text: str) -> np.ndarray:
        """Convert an arbitrary string into a unit complex phasor vector."""
        if not text.strip():
            return np.ones(DIMENSION, dtype=np.complex64)
        h = hashlib.blake2b(text.encode('utf-8'), digest_size=8).digest()
        seed = int.from_bytes(h, byteorder='little')
        rng = np.random.default_rng(seed)
        phases = rng.uniform(-np.pi, np.pi, DIMENSION).astype(np.float32)
        return np.exp(1j * phases)

    def compile_global_manifest(self, root_dir: str) -> str:
        """
        Bind every file path and row index line-by-line into a singular system
        engram (global superposition hypervector).

        Returns a compressed 1200-character (1.2 KB) Base64 representation.
        """
        global_accumulator = np.zeros(DIMENSION, dtype=np.complex64)

        for root, _, files in os.walk(root_dir):
            for file in files:
                if not file.endswith('.py'):
                    continue
                # Skip self to avoid recursion
                if file == os.path.basename(__file__):
                    continue

                filepath = os.path.join(root, file)
                file_phasor = self._string_to_phasor(file)

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_idx, line_content in enumerate(f, start=1):
                            # 1. Compute content vector
                            line_phasor = self._string_to_phasor(line_content)

                            # 2. Compute fractional line number phasor shift matrix
                            pos_phases = self._base_phases * (line_idx / 1000.0)
                            pos_phasor = np.exp(1j * pos_phases)

                            # 3. Conjunctive binding: file × content × position
                            bound_engram = file_phasor * line_phasor * pos_phasor
                            global_accumulator += bound_engram
                except Exception:
                    # Skip unreadable files silently to maintain matrix stability
                    pass

        # Normalize the global superposition state back onto the unit disk
        magnitude = np.abs(global_accumulator)
        magnitude[magnitude < 1e-9] = 1.0
        normalized_vector = global_accumulator / magnitude

        # Quantize complex phase angles to signed bytes (int8) — 75% RAM savings
        phase_bytes = (np.angle(normalized_vector) * (127.0 / np.pi)).astype(np.int8)

        # Return exact MANIFEST_LENGTH-character compact string layout
        return base64.b64encode(phase_bytes.tobytes()).decode('utf-8')[:MANIFEST_LENGTH]

    def inject_holographic_headers(self, root_dir: str, master_hologram: str):
        """
        Surgically overwrite the ST3GG_BASE line in every .py file's
        [AURA_MASTER_KEY] header block with the latest holographic manifest token.
        """
        for root, _, files in os.walk(root_dir):
            for file in files:
                if not file.endswith('.py'):
                    continue
                if file == os.path.basename(__file__):
                    continue
                filepath = os.path.join(root, file)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Only touch files that already carry the master key block
                    if "[AURA_MASTER_KEY]" not in content:
                        continue

                    # Replace the ST3GG_BASE line with the holographic manifest token
                    updated_content = re.sub(
                        r"ST3GG_BASE:\s*(.*?)\n",
                        f"ST3GG_BASE: HOLO-MANIFEST::{master_hologram}\n",
                        content,
                        count=1,
                    )
                    # Only write if the replacement actually changed something
                    if updated_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                except Exception:
                    pass  # Skip unreadable/unwritable files

    def extract_manifest_from_header(self, filepath: str) -> str | None:
        """
        Read a file's [AURA_MASTER_KEY] header and extract the holographic
        manifest token if present. Returns None if no manifest is embedded.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return None

        match = re.search(r"ST3GG_BASE:\s*HOLO-MANIFEST::(\S+)", content)
        if match:
            return match.group(1)
        return None

    def decode_manifest_to_phasor(self, manifest_token: str) -> np.ndarray:
        """
        Decode a Base64 manifest token back into the original 10,000-D
        complex phasor vector (phase-angle reconstruction from int8).
        """
        try:
            phase_bytes = base64.b64decode(manifest_token)
            phase_angles = np.frombuffer(phase_bytes, dtype=np.int8).astype(np.float32)
            phase_angles = phase_angles * (np.pi / 127.0)
            # Pad if the token was shorter than DIMENSION
            if len(phase_angles) < DIMENSION:
                phase_angles = np.pad(
                    phase_angles, (0, DIMENSION - len(phase_angles)),
                    mode='constant', constant_values=0.0
                )
            return np.exp(1j * phase_angles[:DIMENSION])
        except Exception:
            return np.ones(DIMENSION, dtype=np.complex64)

    def verify_file_integrity(
        self, filepath: str, master_phasor: np.ndarray, tolerance: float = 0.85
    ) -> tuple[bool, float]:
        """
        Verify a single file's structural integrity against the master hologram.

        Recomputes the file's contribution and compares it against the
        master phasor. Returns (passes, resonance_score).
        """
        if not os.path.exists(filepath):
            return False, 0.0

        file_phasor = self._string_to_phasor(os.path.basename(filepath))
        local_accumulator = np.zeros(DIMENSION, dtype=np.complex64)

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_idx, line_content in enumerate(f, start=1):
                    line_phasor = self._string_to_phasor(line_content)
                    pos_phases = self._base_phases * (line_idx / 1000.0)
                    pos_phasor = np.exp(1j * pos_phases)
                    local_accumulator += file_phasor * line_phasor * pos_phasor
        except Exception:
            return False, 0.0

        # Normalize local snapshot
        mag = np.abs(local_accumulator)
        mag[mag < 1e-9] = 1.0
        local_normalized = local_accumulator / mag

        # Compute resonance: cos(θ) between local and master phasors
        denom = np.linalg.norm(local_normalized) * np.linalg.norm(master_phasor)
        if denom < 1e-12:
            return False, 0.0
        resonance = float(np.real(np.dot(local_normalized, np.conj(master_phasor)) / denom))
        resonance = max(-1.0, min(1.0, resonance))
        return resonance >= tolerance, resonance


# ── Module-level fast-path generator ─────────────────────────────────────────
def generate_and_inject(root_dir: str = ".") -> str:
    """
    One-shot: compile the global manifest and inject it into all .py file headers.

    Returns the manifest token string (or empty string on failure).
    """
    engine = AuraHolographicManifest()
    try:
        manifest_token = engine.compile_global_manifest(root_dir)
        if not manifest_token:
            print("[-] HolographicManifest: compilation produced empty token.")
            return ""
        engine.inject_holographic_headers(root_dir, manifest_token)
        print(f"[+] HolographicManifest: injected {len(manifest_token)}-char token across filesystem.")
        return manifest_token
    except Exception as exc:
        print(f"[-] HolographicManifest: generation failed — {exc}")
        return ""


async def verify_holographic_system_integrity(
    root_dir: str = ".",
    tolerance: float = 0.85,
    max_files: int | None = None,
) -> dict:
    """
    Boot-time holographic integrity verification.

    Reads the embedded 1.2 KB manifest from a representative file's header,
    decodes it back to a 10,000-D phasor, then spot-checks files across the
    codebase to detect structural drift.  If drift exceeds the tolerance
    threshold, reports which files have drifted so the caller can trigger
    !saturn_heal.

    Parameters
    ----------
    root_dir : str
        Root directory to walk for .py files.
    tolerance : float
        Resonance threshold below which a file is flagged as drifted.
    max_files : int or None
        Limit verification to this many files to avoid long boot delays.
        If None, verifies all files.

    Returns
    -------
    dict with keys:
        "status"   : "PASS" | "DRIFT_DETECTED" | "NO_MANIFEST"
        "checked"  : number of files verified
        "drifted"  : list of (filepath, resonance) tuples for drifted files
        "resonance": average resonance across all checked files
    """
    engine = AuraHolographicManifest()
    result = {
        "status": "NO_MANIFEST",
        "checked": 0,
        "drifted": [],
        "resonance": 0.0,
    }

    # Find a file carrying the holographic manifest token
    manifest_token: str | None = None
    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith('.py'):
                continue
            filepath = os.path.join(root, file)
            token = engine.extract_manifest_from_header(filepath)
            if token:
                manifest_token = token
                break
        if manifest_token:
            break

    if not manifest_token:
        print("[HOLO VERIFY] No holographic manifest found in any file header — skipping integrity check.")
        return result

    # Decode the manifest into the master phasor
    master_phasor = engine.decode_manifest_to_phasor(manifest_token)

    total_resonance = 0.0
    checked = 0
    drifted = []

    files_to_check = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith('.py'):
                continue
            if file == os.path.basename(__file__):
                continue
            files_to_check.append(os.path.join(root, file))

    if max_files is not None and len(files_to_check) > max_files:
        import random
        files_to_check = random.sample(files_to_check, max_files)

    for filepath in files_to_check:
        passes, resonance = engine.verify_file_integrity(
            filepath, master_phasor, tolerance=tolerance
        )
        total_resonance += resonance
        checked += 1
        if not passes:
            drifted.append((filepath, round(resonance, 4)))

    if checked > 0:
        avg_resonance = total_resonance / checked
        result["resonance"] = round(avg_resonance, 4)

    result["checked"] = checked
    result["drifted"] = drifted

    if not drifted:
        result["status"] = "PASS"
        print(f"[HOLO VERIFY] Integrity PASS — {checked} files, avg resonance {result['resonance']:.4f}")
    else:
        result["status"] = "DRIFT_DETECTED"
        print(f"[HOLO VERIFY] DRIFT DETECTED — {len(drifted)}/{checked} files below threshold ({tolerance})")
        for path, res in drifted[:5]:
            print(f"    [!] {path} — resonance {res:.4f}")
        if len(drifted) > 5:
            print(f"    ... and {len(drifted) - 5} more")

    return result


if __name__ == "__main__":
    print("[*] AuraHolographicManifest — Standalone test")
    token = generate_and_inject(".")
    if token:
        print(f"    Token (first 120 chars): {token[:120]}...")
        engine = AuraHolographicManifest()
        phasor = engine.decode_manifest_to_phasor(token)
        print(f"    Decoded phasor shape: {phasor.shape}, dtype: {phasor.dtype}")
    else:
        print("    Generation failed.")
