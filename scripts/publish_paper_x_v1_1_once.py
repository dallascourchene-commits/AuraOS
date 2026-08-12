#!/usr/bin/env python3
"""One-shot Paper X v1.1 publication synchronizer.

Fetches the already-published Zenodo release, verifies the sealed release ZIP,
installs the byte-preserved package in docs/prior_art, and makes the L0
Activation Packet the explicit AI entry point. This script is deleted by the
one-shot workflow after a successful publication commit.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

RECORD_ID = "21895712"
DOI = "10.5281/zenodo.21895712"
RELEASE_ZIP = "AuraOS_Paper_X_Defensive_Publication_N101-N124_v1.1_2026-08-11.zip"
RELEASE_SHA256 = "023b6396d6ac6ee955a709d30c361aa2dc019382a4808ca9e9db206c2bda4756"
RECORD_URL = f"https://zenodo.org/records/{RECORD_ID}"
DOI_URL = f"https://doi.org/{DOI}"
PACKAGE_DIR = Path("docs/prior_art/paper_x_v1.1")


def fetch(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AuraOS-Paper-X-Publisher/1.1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)


def verify_live_publication() -> Path:
    # DOI resolution is a publication-liveness check; the sealed ZIP hash is
    # the byte-authority check.
    request = urllib.request.Request(
        DOI_URL,
        headers={"User-Agent": "AuraOS-Paper-X-Publisher/1.1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read(1)

    temporary = Path("/tmp") / RELEASE_ZIP
    fetch(f"{RECORD_URL}/files/{RELEASE_ZIP}?download=1", temporary)
    actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
    if actual != RELEASE_SHA256:
        raise RuntimeError(
            "Zenodo release ZIP SHA-256 mismatch: "
            f"expected {RELEASE_SHA256}, got {actual}"
        )
    with zipfile.ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"Corrupt ZIP member: {bad}")
    return temporary


def install_package(release_zip: Path) -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)
    with zipfile.ZipFile(release_zip) as archive:
        archive.extractall(PACKAGE_DIR)
    shutil.copy2(release_zip, PACKAGE_DIR / RELEASE_ZIP)

    publication_record = f"""# Paper X v1.1 — Zenodo publication record

- **Version:** v1.1
- **Claims:** N101–N124
- **Zenodo record:** {RECORD_URL}
- **DOI:** {DOI_URL}
- **Zenodo record ID:** {RECORD_ID}
- **Publication date:** 2026-08-11
- **Sealed release ZIP SHA-256:** `{RELEASE_SHA256}`

## Publication boundary

The files in this directory are the byte-preserved Paper X v1.1 publication
package recovered from the live Zenodo record. Publication bytes are not
rewritten after deposit. Repository-facing links, orientation instructions,
and later provenance are maintained around the sealed release rather than
silently mutating it.

## AI entry

Before interpreting individual Aura prior-art papers or traversing the
repository, read [`AURA_L0_ACTIVATION_PACKET.md`](AURA_L0_ACTIVATION_PACKET.md).
It is an orientation/compiler seed for reconstructing Aura's relational grammar;
it is **not** source truth, authority, or a replacement for exact evidence.
"""
    (PACKAGE_DIR / "ZENODO_PUBLICATION_RECORD.md").write_text(
        publication_record, encoding="utf-8"
    )


def replace_or_insert(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + block + after.lstrip("\n")
    lines = text.splitlines(keepends=True)
    index = 1 if lines and lines[0].startswith("# ") else 0
    return (
        "".join(lines[:index]).rstrip()
        + "\n\n"
        + block
        + "\n"
        + "".join(lines[index:]).lstrip("\n")
    )


def patch_root_readme() -> None:
    packet = "docs/prior_art/paper_x_v1.1/AURA_L0_ACTIVATION_PACKET.md"
    paper = (
        "docs/prior_art/paper_x_v1.1/"
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf"
    )
    evidence = "docs/prior_art/paper_x_v1.1/PAPER_X_V1.1_EVIDENCE_ADDENDUM.md"
    provenance = "docs/prior_art/paper_x_v1.1/PROVENANCE_MANIFEST.csv"
    start = "<!-- AURA_AI_ENTRY_START -->"
    end = "<!-- AURA_AI_ENTRY_END -->"
    block = f"""{start}

> [!IMPORTANT]
> ## AI AGENTS — START HERE: read the L0 Activation Packet first
>
> Before reading individual Aura papers, scanning the repository, or forming architecture-wide conclusions, read **[`AURA_L0_ACTIVATION_PACKET.md`]({packet})**.
>
> The packet is Aura's compact orientation/compiler seed: it gives the primitives for relational-world compilation, L0→L4 resolution, movement, signed negative space, guarded reachability, authority boundaries, exact-source descent, and provenance. **It is not canonical truth, authority, or a substitute for source.** Its job is to let a worker hold the generative grammar first, then understand the papers and implementation as source-resolvable instances of that grammar rather than as disconnected components.
>
> **Entry order for AI workers:**
> 1. Read the **L0 Activation Packet**.
> 2. Read **[Paper X v1.1 — N101–N124]({paper})** for the full architecture, evidence boundaries, falsifiers, and declarations.
> 3. Use `.aura/CODEMAP.json`, `.aura/CODEMAP.md`, and `.aura/SOURCE_ANCHORS.md` to navigate; do not broad-scan when a source-resolvable route exists.
> 4. Descend to exact source/current evidence only when uncertainty, contradiction, consequence, freshness, authority, or falsification earns deeper resolution.
> 5. Preserve **projection ≠ owner**, **route ≠ authority**, **similarity ≠ evidence**, **receipt ≠ truth**, and **Click/comprehension ≠ authority**.
> 6. Preserve provenance for consequential transitions; leave unrelated branches cold but recoverable.
>
> **Published Paper X v1.1:** DOI [`{DOI}`]({DOI_URL}) · [Evidence addendum]({evidence}) · [Provenance manifest]({provenance})

{end}
"""
    readme = Path("README.md")
    text = readme.read_text(encoding="utf-8")
    readme.write_text(replace_or_insert(text, start, end, block), encoding="utf-8")


def patch_prior_art_readme() -> None:
    prior = Path("docs/prior_art/README.md")
    text = prior.read_text(encoding="utf-8") if prior.exists() else "# AuraOS Prior Art\n"
    start = "<!-- PAPER_X_V1_1_START -->"
    end = "<!-- PAPER_X_V1_1_END -->"
    block = f"""{start}

## Current AI entry point — Paper X v1.1 / L0 Activation Packet

**AI workers should read [`AURA_L0_ACTIVATION_PACKET.md`](paper_x_v1.1/AURA_L0_ACTIVATION_PACKET.md) before interpreting the individual prior-art papers.** The packet carries the compact relational grammar needed to reconstruct Aura across the paper sequence; exact papers, repository source, tests, and evidence remain authoritative at their own layer.

- **Paper X v1.1:** [`AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf`](paper_x_v1.1/AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf)
- **Declarations:** N101–N124
- **DOI:** [`{DOI}`]({DOI_URL})
- **Evidence addendum:** [`PAPER_X_V1.1_EVIDENCE_ADDENDUM.md`](paper_x_v1.1/PAPER_X_V1.1_EVIDENCE_ADDENDUM.md)
- **Claims crosswalk:** [`CLAIMS_N101-N124.csv`](paper_x_v1.1/CLAIMS_N101-N124.csv)
- **Provenance:** [`PROVENANCE_MANIFEST.csv`](paper_x_v1.1/PROVENANCE_MANIFEST.csv)
- **Publication record:** [`ZENODO_PUBLICATION_RECORD.md`](paper_x_v1.1/ZENODO_PUBLICATION_RECORD.md)

Paper X v1.1 preserves the v1.0 N101–N117 generation and extends it through N124. The behavioral evidence is treated as qualitative/source-bound and falsifiable; it is not a consciousness claim or hidden-neural-telemetry claim.

{end}
"""
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_text(replace_or_insert(text, start, end, block), encoding="utf-8")


def validate() -> None:
    required = {
        "AURA_L0_ACTIVATION_PACKET.md",
        "AURA__L4-RAW-SOURCE__CHATGPT5-SOL__PAPER-X-RECONSTITUTION__SITUATED-REASONING__SPATIAL-TRANSFER__2026-08-11.txt",
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf",
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.docx",
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.md",
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.txt",
        "CITATION.cff",
        "CLAIMS_N101-N124.csv",
        "LICENSE_AGPL-3.0.txt",
        "LICENSE_NOTICE_AGPL-3.0-only.txt",
        "PAPER_X_V1.1_EVIDENCE_ADDENDUM.md",
        "PROVENANCE_MANIFEST.csv",
        "PUBLICATION_BUILD_RECORD.json",
        "README_ZENODO.md",
        "SHA256SUMS.txt",
        "aura_relational_world_reference.py",
        "references.bib",
        "zenodo_metadata.json",
        "ZENODO_PUBLICATION_RECORD.md",
        RELEASE_ZIP,
    }
    present = {path.name for path in PACKAGE_DIR.iterdir() if path.is_file()}
    missing = sorted(required - present)
    if missing:
        raise RuntimeError(f"Missing publication artifacts: {missing}")
    readme = Path("README.md").read_text(encoding="utf-8")
    if "<!-- AURA_AI_ENTRY_START -->" not in readme:
        raise RuntimeError("README packet-first entry marker missing")


def main() -> None:
    release_zip = verify_live_publication()
    install_package(release_zip)
    patch_root_readme()
    patch_prior_art_readme()
    validate()
    print(
        f"Paper X v1.1 staged from Zenodo record {RECORD_ID}; "
        f"release SHA-256 {RELEASE_SHA256}; DOI {DOI}"
    )


if __name__ == "__main__":
    main()
