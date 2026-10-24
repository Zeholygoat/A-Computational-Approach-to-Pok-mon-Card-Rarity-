import math
import pytest

from pokemon_probability_core import (
    probability_at_least_one,
    probability_none,
    expected_hits,
    packs_for_target,
    simulate_at_least_one,
    threshold_table,
)

def test_zero_packs_means_zero_chance():
    assert probability_at_least_one(0, 0.0117) == 0.0
    assert probability_none(0, 0.0117) == 1.0

def test_probability_boundaries():
    assert probability_at_least_one(10, 0.0) == 0.0
    assert probability_at_least_one(1, 1.0) == 1.0
    assert probability_at_least_one(0, 1.0) == 0.0

def test_probability_complement():
    q = probability_at_least_one(100, 0.0117)
    assert math.isclose(q + probability_none(100, 0.0117), 1.0, abs_tol=1e-12)

def test_expected_hits():
    assert math.isclose(expected_hits(100, 0.0117), 1.17)

def test_known_manuscript_thresholds():
    p = 0.0117
    assert packs_for_target(0.90, p) == 196
    assert packs_for_target(0.95, p) == 255
    assert packs_for_target(0.99, p) == 392

def test_threshold_is_minimal():
    p, target = 0.0117, 0.95
    n = packs_for_target(target, p)
    assert probability_at_least_one(n, p) >= target
    assert probability_at_least_one(n - 1, p) < target

def test_zero_and_certain_targets():
    assert packs_for_target(0.0, 0.0) == 0
    assert packs_for_target(0.5, 0.0) is None
    assert packs_for_target(1.0, 1.0) == 1
    assert packs_for_target(1.0, 0.5) is None

def test_validation():
    with pytest.raises(ValueError):
        probability_at_least_one(-1, 0.1)
    with pytest.raises(ValueError):
        probability_at_least_one(10, 1.1)

def test_simulation_is_reproducible():
    a = simulate_at_least_one(100, 0.0117, repetitions=5000, seed=123)
    b = simulate_at_least_one(100, 0.0117, repetitions=5000, seed=123)
    assert a.simulated_probability == b.simulated_probability
    assert a.theoretical_probability == b.theoretical_probability

def test_threshold_table_shape():
    table = threshold_table(0.0117)
    assert len(table) == 7
    assert table["minimum_packs"].iloc[0] < table["minimum_packs"].iloc[-1]
