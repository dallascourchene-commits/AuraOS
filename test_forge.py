import numpy as np

from lexical_transducer import PolysyntheticTransducer


def test_forge_new_root_is_deterministic_and_audited(tmp_path, monkeypatch) -> None:
    """Forge telemetry stays inside the test sandbox and remains deterministic."""
    monkeypatch.chdir(tmp_path)
    english_concept = "artificial neural network"
    ojibwe_concept = "biiwaabik-inawendiwin"
    justification = (
        "Anchoring the concept of an artificial neural network to the Ojibwe root "
        "for synthetic interconnection."
    )

    first = PolysyntheticTransducer().forge_new_root(
        english_concept,
        ojibwe_concept,
        justification,
    )
    second = PolysyntheticTransducer().forge_new_root(
        english_concept,
        ojibwe_concept,
        justification,
    )

    assert first.shape == (12,)
    np.testing.assert_allclose(first, second)
    audit_path = tmp_path / "forged_roots_audit.md"
    audit = audit_path.read_text(encoding="utf-8")
    assert english_concept in audit
    assert ojibwe_concept in audit
    assert justification in audit
