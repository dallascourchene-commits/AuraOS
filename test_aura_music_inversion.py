import math

import numpy as np

from aura_core import SovereignEngine
from aura_mitosis import AuraMitosisEngine
from aura_music_inversion import music_component_search, music_frequency_search


def _circular_frequency_error(found: float, expected: float) -> float:
    delta = abs(found - expected)
    return min(delta, 1.0 - delta)


def test_music_frequency_search_detects_known_complex_tones():
    n = 256
    t = np.arange(n, dtype=np.float32)
    expected = [0.18, 0.33]
    signal = (
        np.exp(1j * 2 * np.pi * expected[0] * t)
        + 0.7 * np.exp(1j * 2 * np.pi * expected[1] * t)
    ).astype(np.complex64)

    result = music_frequency_search(
        signal,
        sample_resolution=1024,
        signal_count=2,
        top_k=4,
        max_subspace_dim=48,
    )
    found = [peak.frequency for peak in result.peaks[:2]]

    assert result.covariance_shape == (48, 48)
    assert result.projected_snapshot_shape[0] == 48
    assert all(any(_circular_frequency_error(freq, target) < 0.004 for freq in found) for target in expected)


def test_music_component_search_detects_projected_high_dimensional_components():
    rng = np.random.default_rng(7)
    dim = 10_000
    snapshot_count = 80
    t = np.arange(snapshot_count, dtype=np.float32)

    c1 = rng.choice([-1.0, 1.0], size=dim).astype(np.float32)
    c1 /= np.linalg.norm(c1)
    c2 = rng.choice([-1.0, 1.0], size=dim).astype(np.float32)
    c2 /= np.linalg.norm(c2)
    distractor = rng.choice([-1.0, 1.0], size=dim).astype(np.float32)
    distractor /= np.linalg.norm(distractor)

    snapshots = (
        np.outer(c1, np.exp(1j * 0.19 * t))
        + 0.9 * np.outer(c2, np.exp(1j * 0.37 * t))
        + 0.01 * (rng.normal(size=(dim, snapshot_count)) + 1j * rng.normal(size=(dim, snapshot_count)))
    ).astype(np.complex64)

    result = music_component_search(
        snapshots,
        {"c1": c1, "c2": c2, "distractor": distractor},
        signal_count=2,
        projection_dim=48,
        top_k=3,
    )
    keys = [peak.key for peak in result.peaks[:2]]

    assert result.source_dimension == dim
    assert result.covariance_shape == (48, 48)
    assert result.projected_snapshot_shape == (48, snapshot_count)
    assert set(keys) == {"c1", "c2"}
    assert result.scores["c1"] > result.scores["distractor"]
    assert result.scores["c2"] > result.scores["distractor"]


def test_mitosis_music_inversion_returns_dominant_frequency_angle():
    frequency = 0.25
    t = np.arange(256, dtype=np.float32)
    signal = np.exp(1j * 2 * np.pi * frequency * t).astype(np.complex64)

    angle = float(AuraMitosisEngine(dimension=10_000).execute_music_inversion(signal, sample_resolution=512))

    assert abs((angle / (2 * math.pi)) - frequency) < 0.003


def test_sovereign_music_inversion_uses_bounded_music_diagnostics():
    engine = SovereignEngine()
    engine.english_decoder = {str(index): f"w{index}" for index in range(64)}

    text = engine.music_inversion((0, 0), engine.vsom_codebook[0, 0], mode="english")

    assert text
    assert hasattr(engine, "last_music_inversion")
    assert engine.last_music_inversion["covariance_shape"][0] <= 48
    assert engine.last_music_inversion["source_dimension"] == 10_000
