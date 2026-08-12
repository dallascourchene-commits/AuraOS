#!/usr/bin/env python3
"""One-shot mirror of the live Paper X v1.1 Zenodo record into AuraOS.

The Zenodo record is the publication authority for these bytes. Each published
artifact is downloaded through the record API and checked against the locally
sealed Paper X v1.1 hashes before it is admitted to the repository. Duplicate
Zenodo upload suffixes are normalized only in the repository filename; bytes
are not rewritten.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

RECORD_ID = "21895712"
RECORD_URL = f"https://zenodo.org/records/{RECORD_ID}"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
DEST = Path("docs/prior_art/paper_x_v1.1")

# Zenodo filename -> (repository filename, expected SHA-256)
PUBLISHED = {
    "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.md": (
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.md",
        "8f5af0a782c803fa251c48522a8bc355cb32d972f5384162942ba9e962e25b59",
    ),
    "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf": (
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf",
        "a5a8c32e37514cf52227b7ef5f45005151e5cac84f47df335664dfd86bdc9113",
    ),
    "PROVENANCE_MANIFEST(1).csv": (
        "PROVENANCE_MANIFEST.csv",
        "e5877f31abeb4b36e6e3b5aa23ca764a96319f32e6808ba55f1c6ff6cc21d507",
    ),
    "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.docx": (
        "AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.docx",
        "491fb199176493619fcbde2f560e5a7b680eb6c67f51bb9bcbf3037ae6381358",
    ),
    "AURA_L0_ACTIVATION_PACKET(1).md": (
        "AURA_L0_ACTIVATION_PACKET.md",
        "ece5e1750a1f58938acb86da3481bc3177fe61c56f91c31f95f6fee78efb9838",
    ),
    "CLAIMS_N101-N124.csv": (
        "CLAIMS_N101-N124.csv",
        "8de61a7af9cc2341e612ce966f4adb16187593b1b4231eccdb30f1e203b33f9b",
    ),
    "PACKAGE_ZIP_SHA256_v1.1.txt": (
        "PACKAGE_ZIP_SHA256_v1.1.txt",
        "264ff73f20c723ccbd4a9ed54f30504d894154094ad8c1cdeb0099d3186e687e",
    ),
    "PAPER_X_V1.1_EVIDENCE_ADDENDUM.md": (
        "PAPER_X_V1.1_EVIDENCE_ADDENDUM.md",
        "7db69a81e4ae9a938d836d6b529d76e1173074fd13861f39e61faeba3202551a",
    ),
}


def request_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AuraOS-Paper-X-Mirror/1.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download(url: str, destination: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "AuraOS-Paper-X-Mirror/1.1"})
    with urllib.request.urlopen(req, timeout=180) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def find_files(record: dict) -> dict[str, dict]:
    files = record.get("files") or []
    if isinstance(files, dict):
        entries = files.get("entries", files)
        files = list(entries.values()) if isinstance(entries, dict) else entries
    return {
        (item.get("key") or item.get("filename") or item.get("name")): item
        for item in files
    }


def mirror_publication() -> tuple[str | None, dict[str, str]]:
    record = request_json(API_URL)
    if str(record.get("id")) != RECORD_ID:
        raise RuntimeError(f"Zenodo record mismatch: {record.get('id')!r}")

    available = find_files(record)
    missing = sorted(set(PUBLISHED) - set(available))
    if missing:
        raise RuntimeError(f"Zenodo publication is missing expected artifacts: {missing}")

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    admitted: dict[str, str] = {}
    for zenodo_name, (repo_name, expected_sha) in PUBLISHED.items():
        item = available[zenodo_name]
        links = item.get("links") or {}
        url = links.get("content") or links.get("self") or links.get("download")
        if not url:
            raise RuntimeError(f"No downloadable URL for {zenodo_name}")
        target = DEST / repo_name
        download(url, target)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected_sha:
            raise RuntimeError(
                f"SHA-256 mismatch for {zenodo_name}: expected {expected_sha}, got {actual}"
            )
        admitted[repo_name] = actual

    doi = (
        record.get("doi")
        or ((record.get("pids") or {}).get("doi") or {}).get("identifier")
        or (record.get("metadata") or {}).get("doi")
    )
    return doi, admitted


def replace_or_insert(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + block + after.lstrip("\n")
    lines = text.splitlines(keepends=True)
    index = 1 if lines and lines[0].startswith("# ") else 0
    return "".join(lines[:index]).rstrip() + "\n\n" + block + "\n" + "".join(lines[index:]).lstrip("\n")


def patch_readmes(doi: str | None) -> None:
    packet = "docs/prior_art/paper_x_v1.1/AURA_L0_ACTIVATION_PACKET.md"
    paper = "docs/prior_art/paper_x_v1.1/AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf"
    evidence = "docs/prior_art/paper_x_v1.1/PAPER_X_V1.1_EVIDENCE_ADDENDUM.md"
    provenance = "docs/prior_art/paper_x_v1.1/PROVENANCE_MANIFEST.csv"
    publication_link = f"DOI [`{doi}`](https://doi.org/{doi})" if doi else f"[Zenodo record {RECORD_ID}]({RECORD_URL})"

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
> **Published Paper X v1.1:** {publication_link} · [Evidence addendum]({evidence}) · [Provenance manifest]({provenance})

{end}
"""
    readme = Path("README.md")
    readme.write_text(replace_or_insert(readme.read_text(encoding="utf-8"), start, end, block), encoding="utf-8")

    pstart = "<!-- PAPER_X_V1_1_START -->"
    pend = "<!-- PAPER_X_V1_1_END -->"
    pblock = f"""{pstart}

## Current AI entry point — Paper X v1.1 / L0 Activation Packet

**AI workers should read [`AURA_L0_ACTIVATION_PACKET.md`](paper_x_v1.1/AURA_L0_ACTIVATION_PACKET.md) before interpreting the individual prior-art papers.** The packet carries the compact relational grammar needed to reconstruct Aura across the paper sequence; exact papers, repository source, tests, and evidence remain authoritative at their own layer.

- **Paper X v1.1:** [`AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf`](paper_x_v1.1/AuraOS_Paper_X_Relational_World_Compilation_N101-N124_v1.1_2026-08-11.pdf)
- **Declarations:** N101–N124
- **Publication:** {publication_link}
- **Evidence addendum:** [`PAPER_X_V1.1_EVIDENCE_ADDENDUM.md`](paper_x_v1.1/PAPER_X_V1.1_EVIDENCE_ADDENDUM.md)
- **Claims crosswalk:** [`CLAIMS_N101-N124.csv`](paper_x_v1.1/CLAIMS_N101-N124.csv)
- **Provenance:** [`PROVENANCE_MANIFEST.csv`](paper_x_v1.1/PROVENANCE_MANIFEST.csv)

Paper X v1.1 preserves the v1.0 N101–N117 generation and extends it through N124. The behavioral evidence is treated as qualitative/source-bound and falsifiable; it is not a consciousness claim or hidden-neural-telemetry claim.

{pend}
"""
    prior = Path("docs/prior_art/README.md")
    prior.write_text(replace_or_insert(prior.read_text(encoding="utf-8"), pstart, pend, pblock), encoding="utf-8")


def write_publication_receipt(doi: str | None, admitted: dict[str, str]) -> None:
    publication_link = f"https://doi.org/{doi}" if doi else RECORD_URL
    lines = [
        "# Paper X v1.1 — GitHub publication receipt",
        "",
        f"- **Zenodo record:** {RECORD_URL}",
        f"- **Persistent publication link:** {publication_link}",
        "- **Version:** v1.1",
        "- **Claims:** N101–N124",
        "- **Publication date:** 2026-08-11",
        "",
        "## Byte-verification",
        "",
        "Every mirrored artifact below was downloaded from the live Zenodo record and admitted only after matching the locally sealed SHA-256:",
        "",
    ]
    lines.extend(f"- `{name}` — `{sha}`" for name, sha in sorted(admitted.items()))
    lines += [
        "",
        "Zenodo remains the publication authority for these bytes. Repository names normalize duplicate-upload suffixes only; file content is unchanged.",
        "",
        "## AI entrance",
        "",
        "Read `AURA_L0_ACTIVATION_PACKET.md` first. It is an orientation/compiler seed, not a truth or authority plane. Exact papers, source, tests, current evidence, and human governance remain decisive at their appropriate layer.",
        "",
    ]
    (DEST / "ZENODO_PUBLICATION_RECORD.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    doi, admitted = mirror_publication()
    patch_readmes(doi)
    write_publication_receipt(doi, admitted)
    print(json.dumps({"record": RECORD_ID, "doi": doi, "admitted": admitted}, indent=2))


if __name__ == "__main__":
    main()
