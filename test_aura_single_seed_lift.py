import numpy as np

from aura_single_seed_lift import (
    DEFAULT_DIMENSIONS,
    LIFT_PROFILE_VERSION,
    compact_lift_capsule,
    compile_text_single_seed_lift,
)


def test_text_single_seed_lift_is_deterministic_and_compact():
    blocks = [
        "cofactor-free single seed lift with cached inverse",
        "trace dispatch reconstructs local context without global recomputation",
    ]

    first = compile_text_single_seed_lift("AURA_TEST", blocks)
    second = compile_text_single_seed_lift("AURA_TEST", blocks)

    assert first.lifted_vector.shape == (DEFAULT_DIMENSIONS,)
    assert first.lifted_vector.dtype == np.complex64
    assert first.profile.version == LIFT_PROFILE_VERSION
    assert first.profile.seed_digest == second.profile.seed_digest
    assert first.profile.inverse_cache_digest == second.profile.inverse_cache_digest
    assert first.profile.complexity_model["source_paper"] == "arXiv:2606.20633"

    capsule = compact_lift_capsule(first.profile)
    assert "SEED=" in capsule
    assert "PATTERN=single_seed_cached_inverse_dispatch" in capsule
    assert len(capsule) <= 360
