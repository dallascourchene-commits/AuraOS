import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parent
MODULE_PATH = ROOT / "glm53_checkpoint_extra_layer_classification.py"
spec = importlib.util.spec_from_file_location("glm53_extra_layer_currentness_type", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

MODEL = "a" * 40
INDEX = "d" * 64
DIGEST = "e" * 64


def observation(current):
    return module.CheckpointExtraLayerEvidenceObservation(
        evidence_ref="drive:glm53-mtp-role",
        evidence_digest=DIGEST,
        evidence_generation="gen:20260830-1",
        resolver_ref="aura:source-evidence-resolver",
        resolver_generation="resolver:1",
        resolution_receipt_ref="drive:glm53-mtp-role-resolution",
        model_revision=MODEL,
        index_sha256=INDEX,
        num_hidden_layers=78,
        roles=((78, "MTP_NON_DECODER"),),
        evidence_current=current,
    )


@pytest.mark.parametrize("impostor", [1, 0, "true", "false", None])
def test_evidence_current_rejects_truthy_or_falsey_non_bool(impostor):
    with pytest.raises(module.ExtraLayerClassificationError) as exc:
        observation(impostor).normalized()
    assert exc.value.code == "EXTRA_LAYER_EVIDENCE_CURRENT_BOOL_REQUIRED"


def test_evidence_current_accepts_only_real_bool_values():
    assert observation(True).normalized()["evidence_current"] is True
    assert observation(False).normalized()["evidence_current"] is False
