"""Extract exact named GitHub workflow run blocks without parsing nested heredocs."""

from __future__ import annotations

from pathlib import Path

SOURCE = Path("tools/construction_release/finalizer.yml")
MAPPING = {
    "Apply fail-closed WebGL2 lifecycle and documentation finalization": Path("/tmp/apply.sh"),
    "Verify source syntax and focused Python contracts": Path("/tmp/verify.sh"),
    "Stress WebGL2 lifecycle and retained Construction rendering": Path("/tmp/stress.sh"),
    "Run focused Coding Waboose review": Path("/tmp/waboose.sh"),
}


def extract(lines: list[str], name: str) -> str:
    marker = f"      - name: {name}"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise RuntimeError(f"finalizer step missing: {name}") from exc
    if start + 1 >= len(lines) or lines[start + 1] != "        run: |":
        raise RuntimeError(f"finalizer run block missing: {name}")

    body: list[str] = []
    for line in lines[start + 2 :]:
        if line.startswith("      - name:") or line.startswith("      - uses:"):
            break
        if line.startswith("          "):
            body.append(line[10:])
        elif not line.strip():
            body.append("")
        else:
            # Nested block-scalar content may carry less indentation after YAML
            # normalization. Preserve it instead of treating it as a new step.
            body.append(line)
    command = "\n".join(body).rstrip()
    if not command:
        raise RuntimeError(f"finalizer command empty: {name}")
    return command


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for name, destination in MAPPING.items():
        destination.write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n" + extract(lines, name) + "\n",
            encoding="utf-8",
        )
        destination.chmod(0o700)
        print(f"extracted {name} -> {destination}")


if __name__ == "__main__":
    main()
