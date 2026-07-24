from __future__ import annotations

from pathlib import Path


def replace_once(source: str, old: str, new: str, *, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return source.replace(old, new, 1)


def patch_toolchain() -> None:
    path = Path("aura_unified_memory_continuity_toolchain.py")
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        "import hashlib\nimport json\nfrom pathlib import Path, PurePosixPath\n",
        "import hashlib\nimport json\nimport math\nfrom pathlib import Path, PurePosixPath\n",
        label="math import",
    )
    source = replace_once(
        source,
        '_LEGAL_OUTCOMES = ("EXECUTE", "VERIFY", "REPAIR", "ESCALATE", "REFUSE")\n',
        '_LEGAL_OUTCOMES = ("EXECUTE", "VERIFY", "REPAIR", "ESCALATE", "REFUSE")\n'
        "_MAX_OBSERVATION_CLOCK_SKEW_SECONDS = 300.0\n",
        label="clock-skew constant",
    )
    source = replace_once(
        source,
        '        returned_model=str(value.get("returned_model") or value.get("requested_model") or ""),\n',
        '        returned_model=_required(value.get("returned_model"), "returned_model"),\n',
        label="explicit returned model",
    )
    source = replace_once(
        source,
        '''def _model_profile(value: Any, *, observed_at: float) -> ModelProfileRef:\n    if not isinstance(value, Mapping):\n        raise ValueError("model_profile must be an object")\n    profile = ModelProfileRef.create(\n        endpoint_identity=_endpoint(value.get("endpoint_identity")),\n        calibrated_at=float(value.get("calibrated_at")),\n        expires_at=float(value.get("expires_at")),\n        evidence_refs=_strings(value.get("evidence_refs"), "model evidence_refs", required=True),\n        uncertainty=float(value.get("uncertainty", 0.5)),\n    )\n    profile.assert_fresh(observed_at=observed_at)\n    return profile\n''',
        '''def _observation_time(value: Any) -> tuple[float, float]:\n    current_time = time.time()\n    observed_at = current_time if value is None else float(value)\n    if not math.isfinite(observed_at):\n        raise ValueError("observed_at must be finite")\n    if abs(observed_at - current_time) > _MAX_OBSERVATION_CLOCK_SKEW_SECONDS:\n        raise ValueError("observed_at exceeds permitted clock skew")\n    return observed_at, current_time\n\n\ndef _model_profile(\n    value: Any,\n    *,\n    observed_at: float,\n    current_time: float,\n) -> ModelProfileRef:\n    if not isinstance(value, Mapping):\n        raise ValueError("model_profile must be an object")\n    calibrated_at = float(value.get("calibrated_at"))\n    expires_at = float(value.get("expires_at"))\n    if not math.isfinite(calibrated_at) or not math.isfinite(expires_at):\n        raise ValueError("model profile timestamps must be finite")\n    if expires_at <= current_time:\n        raise ValueError("model profile has expired")\n    profile = ModelProfileRef.create(\n        endpoint_identity=_endpoint(value.get("endpoint_identity")),\n        calibrated_at=calibrated_at,\n        expires_at=expires_at,\n        evidence_refs=_strings(value.get("evidence_refs"), "model evidence_refs", required=True),\n        uncertainty=float(value.get("uncertainty", 0.5)),\n    )\n    profile.assert_fresh(observed_at=observed_at)\n    profile.assert_fresh(observed_at=current_time)\n    return profile\n''',
        label="current-clock profile validation",
    )
    source = replace_once(
        source,
        '''    observed_at = float(contract.get("observed_at", time.time()))\n    profile = _model_profile(contract.get("model_profile"), observed_at=observed_at)\n''',
        '''    observed_at, current_time = _observation_time(contract.get("observed_at"))\n    profile = _model_profile(\n        contract.get("model_profile"),\n        observed_at=observed_at,\n        current_time=current_time,\n    )\n''',
        label="authoritative observation clock",
    )
    path.write_text(source, encoding="utf-8")


def patch_tests() -> None:
    path = Path("tests/test_aura_unified_memory_continuity_toolchain.py")
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        '''def test_expired_model_profile_rejected(tmp_path: Path) -> None:\n    head = _repo(tmp_path)\n    observed = time.time()\n    contract = _contract(head, now=observed)\n    contract["model_profile"]["expires_at"] = observed - 1\n    with pytest.raises(ValueError, match="Model Cognome profile is not current"):\n        _compile(tmp_path, contract)\n''',
        '''def test_expired_model_profile_rejected(tmp_path: Path) -> None:\n    head = _repo(tmp_path)\n    observed = time.time()\n    contract = _contract(head, now=observed)\n    contract["model_profile"]["expires_at"] = observed - 1\n    with pytest.raises(ValueError, match="model profile has expired"):\n        _compile(tmp_path, contract)\n\n\ndef test_backdated_observation_cannot_reanimate_expired_profile(tmp_path: Path) -> None:\n    head = _repo(tmp_path)\n    current_time = time.time()\n    contract = _contract(head, now=current_time - 120)\n    with pytest.raises(ValueError, match="model profile has expired"):\n        _compile(tmp_path, contract)\n\n\ndef test_observation_time_outside_clock_skew_is_rejected(tmp_path: Path) -> None:\n    head = _repo(tmp_path)\n    contract = _contract(head, now=time.time() - 600)\n    with pytest.raises(ValueError, match="observed_at exceeds permitted clock skew"):\n        _compile(tmp_path, contract)\n\n\ndef test_returned_model_must_be_explicit(tmp_path: Path) -> None:\n    head = _repo(tmp_path)\n    contract = _contract(head)\n    contract["model_profile"]["endpoint_identity"].pop("returned_model")\n    with pytest.raises(ValueError, match="returned_model must not be empty"):\n        _compile(tmp_path, contract)\n''',
        label="final review regressions",
    )
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    patch_toolchain()
    patch_tests()
