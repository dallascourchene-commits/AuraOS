from __future__ import annotations

from pathlib import Path


def test_director_browser_waits_for_exact_p3_presentation_receipt() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "aura_showcase/construction-foundry-director.js"
    ).read_text(encoding="utf-8")
    assert "function waitForP3View" in source
    assert "await waitForP3View(directive.active_view)" in source
    assert 'target?.getAttribute("aria-pressed") === "true"' in source
    assert "stage?.dataset.presentationMode === expectedMode" in source
    assert "requestQueue = requestQueue" in source
