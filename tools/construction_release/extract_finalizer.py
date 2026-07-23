"""Extract exact named GitHub workflow run blocks without parsing nested heredocs."""

from __future__ import annotations

from pathlib import Path

SOURCE = Path("tools/construction_release/finalizer.yml")
APPLY_NAME = "Apply fail-closed WebGL2 lifecycle and documentation finalization"
MAPPING = {
    APPLY_NAME: Path("/tmp/apply.sh"),
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
            body.append(line)
    command = "\n".join(body).rstrip()
    if not command:
        raise RuntimeError(f"finalizer command empty: {name}")
    return command


def normalize_apply_command(command: str) -> str:
    """Make the browser-mode insertion independent of cosmetic JS indentation."""

    start_marker = 'app = Path("aura_spatial_web/construction_demo_app.js")'
    end_marker = 'review_test = Path("tests/js/spatial-construction-review-regressions.test.mjs")'
    start = command.find(start_marker)
    end = command.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("Construction UI patch block missing from reviewed finalizer")

    replacement = r'''app = Path("aura_spatial_web/construction_demo_app.js")
app_text = app.read_text(encoding="utf-8")
if 'state.renderer.setRepresentationMode("SPLATS");' not in app_text:
    anchor = ''' + "'''" + r'''  await state.renderer.initialize(state.packet.scene, state.packet.render_plan, {
    meshPayloads: meshPayloads(state.packet.scene),
    gaussianPayloads: gaussianPayloads(state.packet.scene),
  });
''' + "'''" + r'''
    insertion = anchor + ''' + "'''" + r'''  state.renderer.setRepresentationMode("SPLATS");
  document.querySelectorAll("button[data-mode]").forEach((button) => {
    const supported = button.dataset.mode === "SPLATS";
    button.disabled = !supported;
    button.classList.toggle("active", supported);
    if (!supported) {
      button.title = "Browser GLB decoding and mesh drawing are not implemented; mode is fail-closed";
    }
  });
''' + "'''" + r'''
    if app_text.count(anchor) != 1:
        raise RuntimeError("Construction renderer initialization anchor changed")
    app_text = app_text.replace(anchor, insertion, 1)
    app.write_text(app_text, encoding="utf-8")

'''
    return command[:start] + replacement + command[end:]


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    for name, destination in MAPPING.items():
        command = extract(lines, name)
        if name == APPLY_NAME:
            command = normalize_apply_command(command)
        destination.write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n" + command + "\n",
            encoding="utf-8",
        )
        destination.chmod(0o700)
        print(f"extracted {name} -> {destination}")


if __name__ == "__main__":
    main()
