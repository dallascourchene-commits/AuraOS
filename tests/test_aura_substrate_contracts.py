from __future__ import annotations

from dataclasses import replace

import pytest

from aura_substrate_contracts import SubstrateManifest
from aura_substrate_manifest import build_substrate_manifest


def test_manifest_contract_rejects_migration_and_authority_claims() -> None:
    manifest = build_substrate_manifest()
    phase = manifest.phases[-1]
    for field in (
        "live_owner_changed",
        "callers_redirected",
        "store_transferred",
        "history_backfilled",
        "legacy_deleted",
        "execution_authority_granted",
        "publication_performed",
        "private_reasoning_exported",
    ):
        with pytest.raises(ValueError):
            replace(phase, **{field: True})


def test_manifest_contract_rejects_unsafe_and_duplicate_files() -> None:
    manifest = build_substrate_manifest()
    with pytest.raises(ValueError):
        replace(manifest.files[0], path="../escape.py")
    with pytest.raises(ValueError):
        SubstrateManifest(files=(manifest.files[0], manifest.files[0]), phases=manifest.phases)


def test_manifest_contract_rejects_out_of_order_phase_dependencies() -> None:
    manifest = build_substrate_manifest()
    phases = (manifest.phases[1], manifest.phases[0], *manifest.phases[2:])
    with pytest.raises(ValueError, match="dependencies must precede"):
        SubstrateManifest(files=manifest.files, phases=phases)


def test_generated_topology_and_package_publication_cannot_be_authoritative() -> None:
    manifest = build_substrate_manifest()
    with pytest.raises(ValueError):
        replace(manifest, generated_topology_authoritative=True)
    with pytest.raises(ValueError):
        replace(manifest, package_published=True)
